// ui/src/views/agentic/RunCreator.jsx
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
  NumberInput,
  NumberInputField,
  NumberInputStepper,
  NumberIncrementStepper,
  NumberDecrementStepper,
  Tooltip,
  HStack,
  VStack,
  Alert,
  AlertIcon
} from "@chakra-ui/react";
import { 
  MdLink, 
  MdSpeed, 
  MdSmartToy, 
  MdPlayArrow,
  MdCheckCircle,
  MdSatelliteAlt,
  MdAutoFixHigh,
  MdInfo,
  MdVideocam,
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
  
  // NEW: Auto-healing options
  const [autoHeal, setAutoHeal] = useState(true);
  const [maxHealAttempts, setMaxHealAttempts] = useState(3);
  const [useRecorder, setUseRecorder] = useState(false);

  const bgCard = useColorModeValue("white", "gray.800");
  const borderColor = useColorModeValue("gray.200", "gray.700");
  const textColor = useColorModeValue("gray.900", "white");
  const textColorSecondary = useColorModeValue("gray.600", "gray.400");

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

  /*async function startRun() {
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
        autoHeal,
        maxHealAttempts,
        ...(selectedTemplate && { scenario: selectedTemplate }),
      };
      
      console.log("Starting run with:", payload);
      
      toast({
        title: " Starting Enhanced Test Run...",
        description: autoHeal 
          ? `With auto-healing (up to ${maxHealAttempts} attempts)`
          : "Auto-healing disabled",
        status: "info",
        duration: 3000,
        position: "top",
      });
      
      const res = await axios.post(`${API}/api/run`, payload, { 
        timeout: 100000,
        headers: { 'Content-Type': 'application/json' }
      });
      
      const runId = res.data.runId;
      
      toast({
        title: "✅ Run Started Successfully!",
        description: `Run ID: ${runId.slice(-12)} • Enhanced features active`,
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
  }*/
// In RunCreator.jsx, update the startRun function

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
        mode: useRecorder ? "headed" : mode,  // Force headed if recorder is on
        preset,
        useOllama,
        runName: `ui-run-${Date.now()}`,
        autoHeal,
        maxHealAttempts,
        useRecorder,  // Include recorder option
        ...(selectedTemplate && { scenario: selectedTemplate }),
      };
      
      console.log("Starting run with:", payload);
      
      toast({
        title: "🚀 Starting Enhanced Test Run...",
        description: autoHeal 
          ? `With auto-healing (up to ${maxHealAttempts} attempts)`
          : "Auto-healing disabled",
        status: "info",
        duration: 3000,
        position: "top",
      });
      
      const res = await axios.post(`${API}/api/run`, payload, { 
        timeout: 100000,
        headers: { 'Content-Type': 'application/json' }
      });
      
      const runId = res.data.runId;
      
      console.log("✅ Run started successfully:", runId);
      
      toast({
        title: "✅ Run Started Successfully!",
        description: `Run ID: ${runId.slice(-12)} • Redirecting to progress...`,
        status: "success",
        duration: 2000,
        position: "top",
      });
      
      // ⚠️ CRITICAL: Redirect to progress page instead of dashboard
      setTimeout(() => {
        console.log("Navigating to progress page:", `/admin/progress/${runId}`);
        navigate(`/admin/progress/${runId}`);  // ← CHANGE THIS LINE
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
  const presetInfo = {
    quick: { time: "~2 min", pages: "5 pages", color: "green" },
    balanced: { time: "~5 min", pages: "15 pages", color: "blue" },
    deep: { time: "~10 min", pages: "30 pages", color: "purple" },
  };

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
          <Text color={textColorSecondary} fontSize="md">
            Enhanced with auto-discovery, AI healing & comprehensive reporting
          </Text>
        </Box>

        <Stack spacing="6">
          {/* Main Configuration Card */}
          <Box bg={bgCard} p="8" rounded="xl" shadow="lg" border="1px" borderColor={borderColor}>
            <Stack spacing="6">
              {/* URL Input */}
              <Box>
                <FormLabel fontWeight="bold" mb="3" color={textColor}>
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
                <Text fontSize="xs" color={textColorSecondary} mt="2">
                   Enhanced discovery will extract real selectors from all pages
                </Text>
              </Box>

              <Divider />

              {/* Settings Grid */}
              <Stack direction={{ base: "column", md: "row" }} spacing="6">
                {/* Browser Mode */}
                <Box flex="1">
                  <FormLabel fontWeight="bold" mb="3" color={textColor}>
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
                  <FormLabel fontWeight="bold" mb="3" color={textColor}>
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
                    <option value="quick"> Quick ({presetInfo.quick.time})</option>
                    <option value="balanced"> Balanced ({presetInfo.balanced.time})</option>
                    <option value="deep"> Deep ({presetInfo.deep.time})</option>
                  </Select>
                  <Text fontSize="xs" color={textColorSecondary} mt="2">
                    {presetInfo[preset].pages} discovery depth
                  </Text>
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
                      <Text fontWeight="bold" fontSize="lg" color={textColor}>
                        AI Test Generation
                      </Text>
                    </Flex>
                    <Text fontSize="sm" color={textColorSecondary}>
                      {useOllama 
                        ? "✓ Using Ollama qwen2.5-coder:14b for intelligent test creation" 
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

              {/* NEW: Auto-Healing Section */}
              <Box
                p="5"
                rounded="lg"
                bg={autoHeal ? "blue.50" : "gray.50"}
                border="2px"
                borderColor={autoHeal ? "blue.200" : "gray.200"}
                transition="all 0.3s"
              >
                <VStack align="stretch" spacing="4">
                  <Flex justify="space-between" align="center">
                    <Box>
                      <Flex align="center" mb="1">
                        <Icon as={MdAutoFixHigh} mr="2" color={autoHeal ? "blue.500" : "gray.500"} />
                        <Text fontWeight="bold" fontSize="lg" color={textColor}>
                          Auto-Healing
                        </Text>
                        <Tooltip 
                          label="Automatically fixes failing tests using AI" 
                          placement="top"
                          hasArrow
                        >
                          <span>
                            <Icon as={MdInfo} ml="2" color="gray.400" boxSize="4" />
                          </span>
                        </Tooltip>
                      </Flex>
                      <Text fontSize="sm" color={textColorSecondary}>
                        {autoHeal 
                          ? "✓ AI will automatically fix failing tests and re-run them" 
                          : "Disabled - tests will run once without fixes"}
                      </Text>
                    </Box>
                    <Switch
                      isChecked={autoHeal}
                      onChange={(e) => setAutoHeal(e.target.checked)}
                      size="lg"
                      colorScheme="blue"
                    />
                  </Flex>
                  
                  {/* Healing Attempts Slider */}
                  {autoHeal && (
                    <ScaleFade in={autoHeal} initialScale={0.9}>
                      <Box>
                        <FormLabel fontSize="sm" fontWeight="semibold" mb="2" color={textColor}>
                          Maximum Healing Attempts
                        </FormLabel>
                        <HStack spacing="4">
                          <NumberInput
                            value={maxHealAttempts}
                            onChange={(_, val) => setMaxHealAttempts(val)}
                            min={1}
                            max={5}
                            size="md"
                            maxW="120px"
                          >
                            <NumberInputField />
                            <NumberInputStepper>
                              <NumberIncrementStepper />
                              <NumberDecrementStepper />
                            </NumberInputStepper>
                          </NumberInput>
                          <Text fontSize="sm" color={textColorSecondary}>
                            AI will attempt up to {maxHealAttempts} fix{maxHealAttempts > 1 ? 'es' : ''} per failed test
                          </Text>
                        </HStack>
                        <HStack mt="2" spacing="2">
                          {[1, 2, 3, 4, 5].map(num => (
                            <Badge
                              key={num}
                              colorScheme={maxHealAttempts >= num ? "blue" : "gray"}
                              variant={maxHealAttempts === num ? "solid" : "outline"}
                              cursor="pointer"
                              onClick={() => setMaxHealAttempts(num)}
                              fontSize="xs"
                              px="2"
                              py="1"
                            >
                              {num}
                            </Badge>
                          ))}
                        </HStack>
                      </Box>
                    </ScaleFade>
                  )}
                </VStack>
              </Box>
              <Box
  p="5"
  rounded="lg"
  bg={useRecorder ? "purple.50" : "gray.50"}
  border="2px"
  borderColor={useRecorder ? "purple.200" : "gray.200"}
  transition="all 0.3s"
>
  <Flex justify="space-between" align="center">
    <Box>
      <Flex align="center" mb="1">
        <Icon as={MdVideocam} mr="2" color={useRecorder ? "purple.500" : "gray.500"} />
        <Text fontWeight="bold" fontSize="lg" color={textColor}>
          Visual Test Recorder
        </Text>
        <Tooltip 
          label="Record browser interactions to generate tests" 
          placement="top"
          hasArrow
        >
          <span>
            <Icon as={MdInfo} ml="2" color="gray.400" boxSize="4" />
          </span>
        </Tooltip>
      </Flex>
      <Text fontSize="sm" color={textColorSecondary}>
        {useRecorder 
          ? "✓ Launch recorder to capture manual interactions" 
          : "Generate tests from recorded browser actions"}
      </Text>
    </Box>
    <Switch
      isChecked={useRecorder}
      onChange={(e) => setUseRecorder(e.target.checked)}
      size="lg"
      colorScheme="purple"
    />
  </Flex>

  {/* Recorder Details */}
  {useRecorder && (
    <ScaleFade in={useRecorder} initialScale={0.9}>
      <Box mt="4" p="4" bg="purple.100" rounded="md">
        <VStack align="stretch" spacing="2">
          <Text fontSize="sm" fontWeight="semibold" color="purple.800">
            How it works:
          </Text>
          <HStack spacing="2" fontSize="sm" color="purple.700">
            <Icon as={MdCheckCircle} />
            <Text>Browser opens with recorder overlay</Text>
          </HStack>
          <HStack spacing="2" fontSize="sm" color="purple.700">
            <Icon as={MdCheckCircle} />
            <Text>Perform actions you want to test</Text>
          </HStack>
          <HStack spacing="2" fontSize="sm" color="purple.700">
            <Icon as={MdCheckCircle} />
            <Text>Tests generated from your interactions</Text>
          </HStack>
          <Alert status="info" size="sm" rounded="md" mt="2">
            <AlertIcon />
            <Text fontSize="xs">
              Recorder will open in "headed" mode automatically
            </Text>
          </Alert>
        </VStack>
      </Box>
    </ScaleFade>
  )}
</Box>
            </Stack>
            
          </Box>
          
          {/* Scenario Templates Card */}
          <ScaleFade in={true} initialScale={0.9}>
            <Box bg={bgCard} p="8" rounded="xl" shadow="lg" border="1px" borderColor={borderColor}>
              <Heading size="md" mb="2" color={textColor}>
                 Test Scenario Templates
              </Heading>
              <Text color={textColorSecondary} mb="6" fontSize="sm">
                Select a pre-configured scenario or use auto-discovery
              </Text>

              <Stack spacing="3">
                {SCENARIO_TEMPLATES.map((template) => (
                  <Box
                    key={template.id}
                    p="4"
                    rounded="lg"
                    border="2px"
                    borderColor={selectedTemplate === template.id ? "purple.400" : borderColor}
                    bg={selectedTemplate === template.id ? "purple.50" : bgCard}
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
                      <Box flex="1">
                        <Text fontWeight="semibold" fontSize="md" color={textColor}>
                          {template.name}
                        </Text>
                        <Text fontSize="sm" color={textColorSecondary} mt="1">
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
            loadingText="Launching Enhanced Test..."
            leftIcon={<Icon as={MdPlayArrow} boxSize="8" />}
            transition="all 0.2s"
          >
            {selectedTemplate 
              ? " Start Test with Scenario" 
              : " Start Auto-Discovery Test"}
          </Button>

          {/* Enhanced Features Info Banner */}
          <Box
            p="5"
            rounded="lg"
            bg="blue.50"
            border="1px"
            borderColor="blue.200"
          >
            <VStack align="stretch" spacing="2">
              <Text fontSize="sm" fontWeight="bold" color="blue.800">
                ✨ Enhanced Features Active:
              </Text>
              <HStack flexWrap="wrap" spacing="2">
                <Badge colorScheme="green" fontSize="xs">Enhanced Discovery</Badge>
                {autoHeal && <Badge colorScheme="blue" fontSize="xs">Auto-Healing ({maxHealAttempts}x)</Badge>}
                <Badge colorScheme="purple" fontSize="xs">PostgreSQL Storage</Badge>
                <Badge colorScheme="orange" fontSize="xs">Better Reporting</Badge>
              </HStack>
              <Text fontSize="xs" color="blue.700" mt="1">
                {selectedTemplate 
                  ? "Targeted tests with real selectors and automatic failure recovery"
                  : "Complete site discovery with intelligent selector extraction and self-healing"}
              </Text>
            </VStack>
          </Box>
        </Stack>
      </Box>
    </Fade>
  );
}