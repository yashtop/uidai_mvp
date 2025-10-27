// ui/src/views/agentic/RunCreator.jsx - FIXED VERSION

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
  AlertIcon,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  Textarea,
} from "@chakra-ui/react";
import { 
  MdLink, 
  MdSpeed, 
  MdSmartToy, 
  MdPlayArrow,
  MdCheckCircle,
  MdAutoFixHigh,
  MdInfo,
  MdVideocam,
  MdAutoMode,
  MdBlurOn,
} from "react-icons/md";
import { useNavigate } from "react-router-dom";
import axios from "axios";

const API = process.env.REACT_APP_API_BASE || "http://localhost:8000";

export default function RunCreator() {
  const navigate = useNavigate();
  const toast = useToast();
  
  const [url, setUrl] = useState("https://www.aubank.in/");
  const [mode, setMode] = useState("headless");
  const [preset, setPreset] = useState("quick");
  
  // Test Creation Mode (ai/record/hybrid)
  const [testCreationMode, setTestCreationMode] = useState("ai");
  const [story, setStory] = useState("Test homepage: verify page loads, check navigation menu, test search functionality");
  
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  // Auto-healing options
  const [autoHeal, setAutoHeal] = useState(true);
  const [maxHealAttempts, setMaxHealAttempts] = useState(3);

  const bgCard = useColorModeValue("white", "gray.800");
  const borderColor = useColorModeValue("gray.200", "gray.700");
  const textColor = useColorModeValue("gray.900", "white");
  const textColorSecondary = useColorModeValue("gray.600", "gray.400");

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

    // Validate story for AI mode
    if (testCreationMode === "ai" && !story.trim()) {
      toast({ 
        title: "Story Required", 
        description: "Please provide a test story for AI mode",
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
        testCreationMode,
        story: (testCreationMode === "ai" || testCreationMode === "hybrid") ? story : undefined,
        mode: testCreationMode === "record" ? "headed" : mode,
        preset,
        runName: `ui-run-${Date.now()}`,
        autoHeal,
        maxHealAttempts,
      };
      
      console.log("Starting run with:", payload);
      
      toast({
        title: "🚀 Starting Test Run...",
        description: getModeDescription(testCreationMode),
        status: "info",
        duration: 3000,
        position: "top",
      });
      
      const res = await axios.post(`${API}/api/run`, payload, { 
        timeout: 100000,
        headers: { "Content-Type": "application/json" }
      });
      
      console.log("Full response:", res.data); // Add this
      const runId = res.data.runId;
      console.log("Run ID:", runId);
      
      toast({
        title: "✅ Run Started Successfully!",
        description: `Run ID: ${runId.slice(-12)}`,
        status: "success",
        duration: 2000,
        position: "top",
      });
      
      setTimeout(() => {
        console.log("Navigating to progress page:", `/admin/progress/${runId}`);
        navigate(`/admin/progress/${runId}`);  // ← CHANGE THIS LINE
      }, 1500);
      
    } catch (e) {
      console.error("Start run error:", e);
      
      let errorMessage = "Unknown error occurred";
      if (e.code === "ECONNABORTED") {
        errorMessage = "Request timed out. The server might be busy.";
      } else if (e.response?.data?.detail) {
        errorMessage = e.response.data.detail;
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

  function getModeDescription(modeType) {
    switch(modeType) {
      case "ai": return "AI will generate tests from your story";
      case "record": return "Browser will open for manual recording";
      case "hybrid": return "Record workflow + AI generates additional tests";
      default: return "Starting test run";
    }
  }

  const presetInfo = {
    quick: { time: "~2 min", pages: "5 pages" },
    balanced: { time: "~5 min", pages: "15 pages" },
    deep: { time: "~10 min", pages: "30 pages" },
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
            🚀 Start a Test Run
          </Heading>
          <Text color={textColorSecondary} fontSize="md">
            Choose how you want to create tests: AI, Manual Recording, or Hybrid
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
                    placeholder="https://www.aubank.in/"
                    focusBorderColor="purple.500"
                  />
                </InputGroup>
              </Box>

              <Divider />

              {/* TEST CREATION MODE TABS */}
              <Box>
                <FormLabel fontWeight="bold" mb="3" color={textColor}>
                  <Flex align="center">
                    <Icon as={MdAutoMode} mr="2" color="blue.500" />
                    Test Creation Mode
                  </Flex>
                </FormLabel>

                <Tabs
                  variant="enclosed"
                  colorScheme="purple"
                  index={["ai", "record", "hybrid"].indexOf(testCreationMode)}
                  onChange={(index) => {
                    const modes = ["ai", "record", "hybrid"];
                    setTestCreationMode(modes[index]);
                  }}
                >
                  <TabList>
                    <Tab>
                      <Icon as={MdSmartToy} mr="2" />
                      AI Mode
                    </Tab>
                    <Tab>
                      <Icon as={MdVideocam} mr="2" />
                      Record Mode
                    </Tab>
                    <Tab>
                      <Icon as={MdBlurOn} mr="2" />
                      Hybrid Mode
                    </Tab>
                  </TabList>

                  <TabPanels>
                    {/* AI Mode Panel */}
                    <TabPanel>
                      <VStack align="stretch" spacing="4">
                        <Alert status="info" borderRadius="md">
                          <AlertIcon />
                          AI will automatically generate tests from your story
                        </Alert>

                        <FormLabel fontWeight="semibold" color={textColor}>
                          Test Story (Required)
                        </FormLabel>
                        <Textarea
                          value={story}
                          onChange={(e) => setStory(e.target.value)}
                          placeholder={"Describe what to test. Example:\nTest homepage: verify page loads, check navigation menu, test search functionality"}
                          rows={6}
                          focusBorderColor="purple.500"
                        />
                        <Text fontSize="xs" color={textColorSecondary}>
                          💡 Be specific about what you want to test. The AI will generate test scenarios.
                        </Text>
                      </VStack>
                    </TabPanel>

                    {/* Record Mode Panel */}
                    <TabPanel>
                      <VStack align="stretch" spacing="4">
                        <Alert status="warning" borderRadius="md">
                          <AlertIcon />
                          Browser will open in headed mode for manual recording
                        </Alert>

                        <Box p="4" bg="orange.50" rounded="md" border="1px" borderColor="orange.200">
                          <VStack align="stretch" spacing="2">
                            <Text fontSize="sm" fontWeight="semibold" color="orange.800">
                              How it works:
                            </Text>
                            <HStack spacing="2" fontSize="sm" color="orange.700">
                              <Icon as={MdCheckCircle} />
                              <Text>1. Browser opens with Playwright Inspector</Text>
                            </HStack>
                            <HStack spacing="2" fontSize="sm" color="orange.700">
                              <Icon as={MdCheckCircle} />
                              <Text>2. Perform actions you want to test</Text>
                            </HStack>
                            <HStack spacing="2" fontSize="sm" color="orange.700">
                              <Icon as={MdCheckCircle} />
                              <Text>3. Close browser when done</Text>
                            </HStack>
                            <HStack spacing="2" fontSize="sm" color="orange.700">
                              <Icon as={MdCheckCircle} />
                              <Text>4. Test code generated from your actions</Text>
                            </HStack>
                          </VStack>
                        </Box>

                        <Alert status="info" size="sm" borderRadius="md">
                          <AlertIcon />
                          <Text fontSize="xs">
                            No story needed - your interactions become the test
                          </Text>
                        </Alert>
                      </VStack>
                    </TabPanel>

                    {/* Hybrid Mode Panel */}
                    <TabPanel>
                      <VStack align="stretch" spacing="4">
                        <Alert status="success" borderRadius="md">
                          <AlertIcon />
                          Record workflow, then AI generates additional tests
                        </Alert>

                        <FormLabel fontWeight="semibold" color={textColor}>
                          Additional Test Story (Optional)
                        </FormLabel>
                        <Textarea
                          value={story}
                          onChange={(e) => setStory(e.target.value)}
                          placeholder={"Optional: Describe additional tests.\nExample: Add edge cases with invalid inputs and error handling"}
                          rows={5}
                          focusBorderColor="purple.500"
                        />
                        <Text fontSize="xs" color={textColorSecondary}>
                          💡 First record your workflow, then AI generates additional scenarios
                        </Text>

                        <Box p="4" bg="green.50" rounded="md" border="1px" borderColor="green.200">
                          <Text fontSize="sm" fontWeight="semibold" color="green.800" mb="2">
                            Best of Both Worlds:
                          </Text>
                          <VStack align="stretch" spacing="1" fontSize="xs" color="green.700">
                            <Text>✓ Manual workflow for critical paths</Text>
                            <Text>✓ AI-generated edge case tests</Text>
                            <Text>✓ Comprehensive coverage</Text>
                          </VStack>
                        </Box>
                      </VStack>
                    </TabPanel>
                  </TabPanels>
                </Tabs>
              </Box>

              <Divider />

              {/* Execution Settings */}
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
                    isDisabled={testCreationMode === "record"}
                  >
                    <option value="headless">🚀 Headless (Faster)</option>
                    <option value="headed">👁️ Headed (Visual)</option>
                  </Select>
                  {testCreationMode === "record" && (
                    <Text fontSize="xs" color="orange.600" mt="2">
                      Record mode uses headed browser
                    </Text>
                  )}
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
                    <option value="quick">⚡ Quick ({presetInfo.quick.time})</option>
                    <option value="balanced">⚖️ Balanced ({presetInfo.balanced.time})</option>
                    <option value="deep">🔍 Deep ({presetInfo.deep.time})</option>
                  </Select>
                </Box>
              </Stack>

              {/* Auto-Healing */}
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
                          ? "✓ AI will fix failing tests and re-run" 
                          : "Disabled - tests run once"}
                      </Text>
                    </Box>
                    <Switch
                      isChecked={autoHeal}
                      onChange={(e) => setAutoHeal(e.target.checked)}
                      size="lg"
                      colorScheme="blue"
                    />
                  </Flex>
                  
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
                            Up to {maxHealAttempts} fix{maxHealAttempts > 1 ? "es" : ""} per test
                          </Text>
                        </HStack>
                      </Box>
                    </ScaleFade>
                  )}
                </VStack>
              </Box>
            </Stack>
          </Box>

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
            loadingText="Launching..."
            leftIcon={<Icon as={MdPlayArrow} boxSize="8" />}
            transition="all 0.2s"
          >
            {testCreationMode === "ai" && "🤖 Start AI Test Generation"}
            {testCreationMode === "record" && "🎬 Start Recording Session"}
            {testCreationMode === "hybrid" && "🔀 Start Hybrid Testing"}
          </Button>

          {/* Info Banner */}
          <Box p="5" rounded="lg" bg="blue.50" border="1px" borderColor="blue.200">
            <VStack align="stretch" spacing="2">
              <Text fontSize="sm" fontWeight="bold" color="blue.800">
                ✨ Active Features:
              </Text>
              <HStack flexWrap="wrap" spacing="2">
                <Badge 
                  colorScheme={
                    testCreationMode === "ai" ? "purple" : 
                    testCreationMode === "record" ? "orange" : "green"
                  } 
                  fontSize="xs"
                >
                  {testCreationMode.toUpperCase()} Mode
                </Badge>
                {autoHeal && (
                  <Badge colorScheme="blue" fontSize="xs">
                    Auto-Healing ({maxHealAttempts}x)
                  </Badge>
                )}
                <Badge colorScheme="purple" fontSize="xs">PostgreSQL Storage</Badge>
                <Badge colorScheme="green" fontSize="xs">Real-time Progress</Badge>
              </HStack>
            </VStack>
          </Box>
        </Stack>
      </Box>
    </Fade>
  );
}