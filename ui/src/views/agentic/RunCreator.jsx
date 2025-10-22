import React, { useState } from "react";
import {
  Box,
  Stack,
  Heading,
  Input,
  Select,
  Switch,
  Button,
  FormLabel,
  useToast,
  Text,
  Divider,
  Badge,
  Flex,
  Icon,
  ScaleFade,
  Fade,
  useColorModeValue,
  InputGroup,
  InputLeftElement,
} from "@chakra-ui/react";
import { 
  MdLink, 
  MdSpeed, 
  MdSmartToy, 
  MdPlayArrow,
  MdCheckCircle,
  MdSatelliteAlt
} from "react-icons/md";
import { useNavigate } from "react-router-dom";
import axios from "axios";

const API = process.env.REACT_APP_API_BASE || "http://localhost:8000";

const SCENARIO_TEMPLATES = [
  {
    id: "uidai-homepage-navigation",
    name: "1. UIDAI Homepage & Main Navigation",
    description: "Test UIDAI English homepage structure and primary navigation",
  },
  {
    id: "uidai-my-aadhaar-services",
    name: "2. My Aadhaar Services Discovery",
    description: "Test My Aadhaar section and service pages"
  },
  {
    id: "uidai-about-contact",
    name: "3. About UIDAI & Contact Pages",
    description: "Test About UIDAI and Contact/Support pages"
  },
  {
    id: "uidai-enrolment-centers",
    name: "4. Locate Enrolment Centers",
    description: "Test enrolment center locator functionality"
  },
  {
    id: "uidai-faqs-help",
    name: "5. FAQs & Help Resources",
    description: "Test FAQ section and help resources"
  },
  {
    id: "uidai-downloads-resources",
    name: "6. Downloads & Resources Section",
    description: "Test downloads, forms, and resource materials"
  },
];

export default function RunCreator() {
  const navigate = useNavigate();
  const toast = useToast();
  
  const [url, setUrl] = useState("https://uidai.gov.in/en/");
  const [mode, setMode] = useState("headless");
  const [preset, setPreset] = useState("quick");
  const [useOllama, setUseOllama] = useState(true);
  const [selectedTemplate, setSelectedTemplate] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const bgCard = useColorModeValue("white", "gray.800");
  const borderColor = useColorModeValue("gray.200", "gray.700");

  const loadTemplate = (templateId) => {
    setSelectedTemplate(templateId);
    const template = SCENARIO_TEMPLATES.find(t => t.id === templateId);
    if (template) {
      toast({
        title: "Template selected",
        description: template.name,
        status: "info",
        duration: 2000,
        position: "top",
      });
    }
  };

  async function startRun() {
    if (isSubmitting) return;
    
    if (!/^https?:\/\//.test(url)) {
      toast({ 
        title: "Invalid URL", 
        description: "URL must start with http:// or https://",
        status: "error", 
        duration: 3000,
        position: "top",
      });
      return;
    }
    
    setIsSubmitting(true);
    
    try {
      const payload = {
        url,
        mode,
        preset,
        useOllama,
        runName: `ui-run-${Date.now()}`,
        maxHealAttempts: 1,
        ...(selectedTemplate && { scenario: selectedTemplate }),
      };
      
      console.log("Starting run with:", payload);
      
      if (!selectedTemplate) {
        toast({
          title: "🔍 Starting Auto-Discovery...",
          description: "This may take 30-60 seconds",
          status: "info",
          duration: 3000,
          position: "top",
        });
      }
      
      const res = await axios.post(`${API}/api/run`, payload, { 
        timeout: 60000,
        headers: { 'Content-Type': 'application/json' }
      });
      
      const runId = res.data.runId;
      
      toast({
        title: "✅ Run Started Successfully!",
        description: `Run ID: ${runId.slice(-12)}`,
        status: "success",
        duration: 4000,
        position: "top",
      });
      
      setTimeout(() => {
        navigate("/admin/runs");
      }, 1500);
      
    } catch (e) {
      console.error("Start run error:", e);
      
      let errorMessage = "Unknown error occurred";
      if (e.code === 'ECONNABORTED') {
        errorMessage = "Request timed out. The server might be busy. Please try again.";
      } else if (e.response?.data?.detail) {
        errorMessage = e.response.data.detail;
      } else if (e.response?.data?.error) {
        errorMessage = e.response.data.error;
      } else if (e.message) {
        errorMessage = e.message;
      }
      
      toast({
        title: "Failed to start run",
        description: errorMessage,
        status: "error",
        duration: 6000,
        isClosable: true,
        position: "top",
      });
    } finally {
      setTimeout(() => setIsSubmitting(false), 1000);
    }
  }

  return (
    <Fade in={true}>
      <Box maxW="1200px" mx="auto">
        {/* Header */}
        <Box mb="8">
          <Heading 
            size="xl" 
            bgGradient="linear(to-r, purple.600, pink.500)"
            bgClip="text"
            mb="2"
          >
            Start a Test Run
          </Heading>
          <Text color="gray.600" fontSize="md">
            Configure and launch automated tests for UIDAI portal
          </Text>
        </Box>

        <Stack spacing="6">
          {/* Configuration Card */}
          <Box bg={bgCard} p="8" rounded="xl" shadow="lg" border="1px" borderColor={borderColor}>
            <Stack spacing="6">
              {/* URL Input */}
              <Box>
                <FormLabel fontWeight="bold" mb="3">
                  <Flex align="center">
                    <Icon as={MdLink} mr="2" color="purple.500" />
                    Target URL
                  </Flex>
                </FormLabel>
                <InputGroup size="lg">
                  <InputLeftElement pointerEvents="none">
                    <Icon as={MdLink} color="gray.400" />
                  </InputLeftElement>
                  <Input
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    placeholder="https://uidai.gov.in/en/"
                    focusBorderColor="purple.500"
                  />
                </InputGroup>
                <Text fontSize="xs" color="gray.500" mt="2">
                  Enter the base URL to test
                </Text>
              </Box>

              <Divider />

              {/* Settings Grid */}
              <Stack direction={{ base: "column", md: "row" }} spacing="6">
                {/* Browser Mode */}
                <Box flex="1">
                  <FormLabel fontWeight="bold" mb="3">
                    Browser Mode
                  </FormLabel>
                  <Select 
                    value={mode} 
                    onChange={(e) => setMode(e.target.value)} 
                    size="lg"
                    focusBorderColor="purple.500"
                  >
                    <option value="headless"> Headless (Faster)</option>
                    <option value="headed"> Headed (Visual)</option>
                  </Select>
                </Box>

                {/* Test Depth */}
                <Box flex="1">
                  <FormLabel fontWeight="bold" mb="3">
                    <Flex align="center">
                      <Icon as={MdSpeed} mr="2" color="blue.500" />
                      Test Depth
                    </Flex>
                  </FormLabel>
                  <Select 
                    value={preset} 
                    onChange={(e) => setPreset(e.target.value)} 
                    size="lg"
                    focusBorderColor="purple.500"
                  >
                    <option value="quick"> Quick (2 min)</option>
                    <option value="balanced"> Balanced (5 min)</option>
                    <option value="deep"> Deep (10 min)</option>
                  </Select>
                </Box>
              </Stack>

              {/* AI Toggle */}
              <Box
                p="5"
                rounded="lg"
                bg={useOllama ? "green.50" : "gray.50"}
                border="2px"
                borderColor={useOllama ? "green.200" : "gray.200"}
                transition="all 0.3s"
              >
                <Flex justify="space-between" align="center">
                  <Box>
                    <Flex align="center" mb="1">
                      <Icon as={MdSmartToy} mr="2" color={useOllama ? "green.500" : "gray.500"} />
                      <Text fontWeight="bold" fontSize="lg">
                        AI Test Generation
                      </Text>
                    </Flex>
                    <Text fontSize="sm" color="gray.600">
                      {useOllama 
                        ? "✓ Using Ollama local LLM for intelligent test creation" 
                        : "Using basic stub tests"}
                    </Text>
                  </Box>
                  <Switch
                    isChecked={useOllama}
                    onChange={(e) => setUseOllama(e.target.checked)}
                    size="lg"
                    colorScheme="green"
                  />
                </Flex>
              </Box>
            </Stack>
          </Box>

          {/* Scenario Templates Card */}
          <ScaleFade in={true} initialScale={0.9}>
            <Box bg={bgCard} p="8" rounded="xl" shadow="lg" border="1px" borderColor={borderColor}>
              <Heading size="md" mb="2">
                 Test Scenario Templates
              </Heading>
              <Text color="gray.600" mb="6" fontSize="sm">
                Select a pre-configured scenario or use auto-discovery
              </Text>

              <Stack spacing="3">
                {SCENARIO_TEMPLATES.map((template) => (
                  <Box
                    key={template.id}
                    p="4"
                    rounded="lg"
                    border="2px"
                    borderColor={selectedTemplate === template.id ? "purple.400" : "gray.200"}
                    bg={selectedTemplate === template.id ? "purple.50" : "white"}
                    cursor="pointer"
                    onClick={() => loadTemplate(template.id)}
                    transition="all 0.2s"
                    _hover={{
                      borderColor: "purple.300",
                      transform: "translateY(-2px)",
                      shadow: "md",
                    }}
                  >
                    <Flex align="center">
                      <Text fontSize="2xl" mr="3">{template.icon}</Text>
                      <Box flex="1">
                        <Text fontWeight="semibold" fontSize="md">
                          {template.name}
                        </Text>
                        <Text fontSize="sm" color="gray.600" mt="1">
                          {template.description}
                        </Text>
                      </Box>
                      {selectedTemplate === template.id && (
                        <Icon as={MdCheckCircle} color="purple.500" boxSize="6" />
                      )}
                    </Flex>
                  </Box>
                ))}
              </Stack>

              {selectedTemplate && (
                <Button
                  size="sm"
                  variant="ghost"
                  colorScheme="red"
                  onClick={() => setSelectedTemplate("")}
                  w="full"
                  mt="4"
                >
                  Clear Selection
                </Button>
              )}
            </Box>
          </ScaleFade>

          {/* Launch Button */}
          <Button
            size="xl"
            h="70px"
            fontSize="xl"
            fontWeight="bold"
            bgGradient="linear(to-r, purple.500, pink.500)"
            color="white"
            _hover={{
              bgGradient: "linear(to-r, purple.600, pink.600)",
              transform: "translateY(-2px)",
              shadow: "xl",
            }}
            _active={{
              transform: "translateY(0)",
            }}
            onClick={startRun}
            isLoading={isSubmitting}
            loadingText="Launching Test Run..."
            leftIcon={<Icon as={MdPlayArrow} boxSize="8" />}
            transition="all 0.2s"
          >
            {selectedTemplate 
              ? " Start Test with Scenario" 
              : " Start Auto-Discovery Test"}
          </Button>

          {/* Info Banner */}
          <Box
            p="5"
            rounded="lg"
            bg={selectedTemplate ? "blue.50" : "gray.50"}
            border="1px"
            borderColor={selectedTemplate ? "blue.200" : "gray.200"}
          >
            <Flex align="center">
              <Text fontSize="3xl" mr="3">
                {selectedTemplate ?  <Icon as={MdLink} mr="2" color="purple.500" /> :  <Icon as={MdSatelliteAlt} mr="2" color="purple.500" />}
              </Text>
             
              <Text fontSize="sm" color="gray.700">
                {selectedTemplate 
                  ? "AI will generate targeted tests based on your selected scenario"
                  : "Without a scenario, AI will automatically discover and test all available pages"}
              </Text>
            </Flex>
          </Box>
        </Stack>
      </Box>
    </Fade>
  );
}