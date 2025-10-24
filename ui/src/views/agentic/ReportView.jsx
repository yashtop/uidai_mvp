import React, { useEffect, useState } from "react";
import {
  Box,
  Heading,
  Text,
  Spinner,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  VStack,
  HStack,
  Badge,
  Card,
  CardBody,
  SimpleGrid,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  Button,
  ButtonGroup,
  Divider,
  Fade,
  Icon,
} from "@chakra-ui/react";
import { useParams, useNavigate } from "react-router-dom";
import { MdCheckCircle, MdCancel, MdAccessTime, MdSpeed, MdReport, MdRefresh, MdVideocam, MdVisibility } from "react-icons/md";
import axios from "axios";

const API = process.env.REACT_APP_API_BASE || "http://localhost:8000";

export default function ReportView() {
  const { runId } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [runData, setRunData] = useState(null);
  const [isRecorder, setIsRecorder] = useState(false);
  const [isHeaded, setIsHeaded] = useState(false);

  useEffect(() => {
    loadReport();
  }, [runId]);
 
  async function loadReport() {
    setLoading(true);
    setError(null);
    try {
      // Get full run data from main endpoint
      const res = await axios.get(`${API}/api/run/${runId}`);
      console.log("Run data loaded:", res.data);
      
      if (res.data && res.data.runId) {
        setRunData(res.data);
        
        // ← DETECT RECORDER MODE
        const isRecorderMode = 
          res.data.tests?.mode === "recorder" ||
          res.data.discovery?.stats?.mode === "recorder" ||
          res.data.config?.useRecorder === true;
        
        console.log("Recorder mode detected:", isRecorderMode);
        setIsRecorder(isRecorderMode);
        
        // ← DETECT HEADED MODE
        const headedMode = res.data.config?.mode === "headed" || isRecorderMode;
        console.log("Headed mode detected:", headedMode);
        setIsHeaded(headedMode);
      } else {
        setError("Run data not available");
      }
    } catch (e) {
      console.error("Failed to load report:", e);
      setError(e.response?.data?.detail || e.message || "Failed to load report");
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <Box p="6" textAlign="center">
        <Spinner size="xl" color="purple.500" thickness="4px" mb="4" />
        <Text color="gray.600">Loading comprehensive report...</Text>
      </Box>
    );
  }

  if (error) {
    return (
      <Box p="6">
        <Alert status="warning" rounded="md">
          <AlertIcon />
          <Box>
            <AlertTitle>Report Not Available</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Box>
        </Alert>
        <Button mt="4" colorScheme="purple" onClick={() => navigate("/admin/runs")}>
          Back to Dashboard
        </Button>
      </Box>
    );
  }

  if (!runData) {
    return (
      <Box p="6">
        <Alert status="info" rounded="md">
          <AlertIcon />
          No report data available
        </Alert>
        <Button mt="4" colorScheme="purple" onClick={() => navigate("/admin/runs")}>
          Back to Dashboard
        </Button>
      </Box>
    );
  }

  // Extract basic info
  const targetUrl = runData.targetUrl || "Unknown";
  const status = runData.status || "unknown";
  const createdAt = runData.createdAt;
  const completedAt = runData.completedAt;
  const scenario = runData.config?.scenario || "auto-discovery";

  // Calculate duration
  let durationMin = "N/A";
  let durationSec = 0;
  if (completedAt && createdAt) {
    try {
      const start = new Date(createdAt).getTime();
      const end = new Date(completedAt).getTime();
      durationSec = (end - start) / 1000;
      durationMin = (durationSec / 60).toFixed(1);
    } catch (e) {
      console.error("Error calculating duration:", e);
    }
  }

  // Extract discovery data
  const discoveryPages = runData.discovery?.pages || [];
  const pagesCount = discoveryPages.length;
  const elementsCount = discoveryPages.reduce((sum, p) => sum + (p.selectors?.length || 0), 0);
  const discoveryOk = pagesCount > 0 || isRecorder; // ← OK if recorder mode

  // Extract tests data
  const testsData = runData.tests || {};
  const testsCount = testsData.count || testsData.tests?.length || 0;
  const testsOk = testsCount > 0;

  // Extract results data with proper type conversion
  const resultsData = runData.results || {};
  const resultsSummary = resultsData.summary || {};
  
  // CRITICAL: Convert string numbers to integers
  const totalTests = parseInt(resultsSummary.total) || parseInt(resultsSummary.collected) || 0;
  const passedTests = parseInt(resultsSummary.passed) || 0;
  const failedTests = parseInt(resultsSummary.failed) || 0;
  const skippedTests = parseInt(resultsSummary.skipped) || 0;
  
  // Check if results are OK (handle both number and string)
  const exitCode = resultsData.exitCode;
  const resultsOk = exitCode === 0 || exitCode === "0";
  
  // Calculate pass rate with proper logic
  let passRate = "0";
  if (totalTests > 0) {
    passRate = ((passedTests / totalTests) * 100).toFixed(1);
  } else if (resultsOk && passedTests > 0) {
    // If exitCode is 0 but we have no total, assume all passed
    passRate = "100";
  }
  
  console.log("Results debug:", {
    totalTests,
    passedTests,
    failedTests,
    exitCode,
    resultsOk,
    passRate,
    raw: runData
  });

  // Healing data
  const healingData = runData.healing || {};
  const healingOk = healingData.ok || false;

  // Format scenario name
  const scenarioName = scenario === "auto-discovery" 
    ? "AUTO-DISCOVERY"
    : scenario.replace(/-/g, ' ').split(' ').map(w => 
        w.charAt(0).toUpperCase() + w.slice(1)
      ).join(' ');

  // Get pass rate color
  const getPassRateColor = (rate) => {
    const numRate = parseFloat(rate);
    if (numRate >= 80) return "green.600";
    if (numRate >= 50) return "orange.600";
    if (numRate > 0) return "red.600";
    return "gray.600";
  };

  return (
    <Fade in={true}>
      <Box p="6" maxW="1400px" mx="auto">
        <VStack align="stretch" spacing="6">
          {/* Header */}
          <HStack justify="space-between" align="start" flexWrap="wrap">
            <Box>
              <Heading 
                size="xl" 
                mb="2"
                bgGradient="linear(to-r, purple.600, pink.500)"
                bgClip="text"
              >
                Test Run Report
              </Heading>
              <Text color="gray.600" fontSize="sm" mb="1">
                Run ID: <Badge fontFamily="monospace" fontSize="xs" colorScheme="purple">{runId.slice(-12)}</Badge>
              </Text>
              <Text color="gray.600" fontSize="sm">
                Target: <Badge colorScheme="blue" fontSize="xs">{targetUrl}</Badge>
              </Text>
            </Box>
            <ButtonGroup size="sm" flexWrap="wrap">
              <Button colorScheme="purple" onClick={() => navigate(`/admin/discovery/${runId}`)}>
               Discovery
              </Button>
              <Button colorScheme="blue" onClick={() => navigate(`/admin/tests/${runId}`)}>
                Tests
              </Button>
              <Button colorScheme="pink" onClick={() => navigate(`/admin/healing/${runId}`)}>
                Healing
              </Button>
              <Button 
                colorScheme="red" 
                onClick={() => navigate(`/admin/failures/${runId}`)}
                isDisabled={status == "completed" && status == "failed"}
              >
                 Test Failures with Screenshots
              </Button>
              <Button 
                colorScheme="green" 
                onClick={() => navigate(`/admin/results/${runId}`)}
                isDisabled={status !== "completed" && status !== "failed"}
              >
                 Results
              </Button>
            </ButtonGroup>
          </HStack>

          {/* Status Banner */}
          <Alert
            status={status === "completed" ? "success" : status === "failed" ? "error" : "info"}
            rounded="lg"
            boxShadow="lg"
          >
            <AlertIcon />
            <Box flex="1">
              <AlertTitle fontSize="lg" fontWeight="bold">
                Status: {status.toUpperCase()}
              </AlertTitle>
              <AlertDescription fontSize="sm">
                Run {status === "completed" ? "completed successfully" : status === "failed" ? "encountered errors" : "in progress"}
                {completedAt && ` at ${new Date(completedAt).toLocaleString()}`}
              </AlertDescription>
            </Box>
            {/* ← ADD MODE BADGES */}
            <VStack align="end" spacing="1">
              {isRecorder && (
                <Badge colorScheme="purple" fontSize="md" px="3" py="1">
                  <Icon as={MdVideocam} mr="1" />
                  RECORDER
                </Badge>
              )}
              {isHeaded && (
                <Badge colorScheme="cyan" fontSize="md" px="3" py="1">
                  <Icon as={MdVisibility} mr="1" />
                  HEADED
                </Badge>
              )}
            </VStack>
          </Alert>

          {/* ← ADD RECORDER ALERT */}
          {isRecorder && (
            <Alert status="info" rounded="lg" variant="left-accent" borderLeftWidth="4px">
              <AlertIcon />
              <Box>
                <Text fontWeight="bold" fontSize="md">
                  🎥 Visual Test Recorder Mode
                </Text>
                <Text fontSize="sm" color="gray.600" mt="1">
                  This test was created manually using the Visual Test Recorder.
                  Discovery and AI generation were skipped. Test ran in visible browser mode.
                </Text>
              </Box>
            </Alert>
          )}

          {/* Run Configuration */}
          <Card boxShadow="lg">
            <CardBody>
              <Heading size="sm" mb="3" color="gray.700">Run Configuration</Heading>
              <HStack spacing="6" flexWrap="wrap">
                <Box>
                  <Text fontSize="xs" color="gray.500">Test Mode</Text>
                  <Badge colorScheme="blue" fontSize="sm" mt="1">
                    {isRecorder ? "MANUAL RECORDING" : "AI GENERATED"}
                  </Badge>
                </Box>
                <Box>
                  <Text fontSize="xs" color="gray.500">Browser Mode</Text>
                  <Badge colorScheme={isHeaded ? "cyan" : "gray"} fontSize="sm" mt="1">
                    {isHeaded ? "HEADED (Visible)" : "HEADLESS"}
                  </Badge>
                </Box>
                <Box>
                  <Text fontSize="xs" color="gray.500">Scenario</Text>
                  <Badge colorScheme="purple" fontSize="sm" mt="1">
                    {scenarioName}
                  </Badge>
                </Box>
              </HStack>
            </CardBody>
          </Card>

          {/* Summary Statistics */}
          <Box>
            <Heading size="md" mb="4" color="gray.700">
               <Icon as={MdReport} mb="-1px" mr="1" /> Summary
            </Heading>
            <SimpleGrid columns={{ base: 2, md: 5 }} spacing="4">
              {/* Pages */}
              <Card boxShadow="lg" _hover={{ transform: "translateY(-4px)", transition: "all 0.2s" }}>
                <CardBody>
                  <Stat>
                    <StatLabel fontSize="xs" color="gray.600">Pages</StatLabel>
                    <StatNumber 
                      fontSize="2xl" 
                      color="blue.600"
                      fontWeight="bold"
                    >
                      {pagesCount}
                    </StatNumber>
                    <StatHelpText fontSize="xs">
                      {isRecorder ? "Manual Test" : "Discovered"}
                    </StatHelpText>
                  </Stat>
                </CardBody>
              </Card>

              {/* Elements */}
              <Card boxShadow="lg" _hover={{ transform: "translateY(-4px)", transition: "all 0.2s" }}>
                <CardBody>
                  <Stat>
                    <StatLabel fontSize="xs" color="gray.600">Elements</StatLabel>
                    <StatNumber fontSize="3xl" color="green.600" fontWeight="bold">
                      {elementsCount}
                    </StatNumber>
                    <StatHelpText fontSize="xs">
                      {isRecorder ? "N/A" : "Found"}
                    </StatHelpText>
                  </Stat>
                </CardBody>
              </Card>

              {/* Tests */}
              <Card boxShadow="lg" _hover={{ transform: "translateY(-4px)", transition: "all 0.2s" }}>
                <CardBody>
                  <Stat>
                    <StatLabel fontSize="xs" color="gray.600">Tests</StatLabel>
                    <StatNumber fontSize="3xl" color="purple.600" fontWeight="bold">
                      {testsCount}
                    </StatNumber>
                    <StatHelpText fontSize="xs">
                      {isRecorder ? "Recorded" : "Generated"}
                    </StatHelpText>
                  </Stat>
                </CardBody>
              </Card>

              {/* Pass Rate */}
              <Card boxShadow="lg" _hover={{ transform: "translateY(-4px)", transition: "all 0.2s" }}>
                <CardBody>
                  <Stat>
                    <StatLabel fontSize="xs" color="gray.600">Pass Rate</StatLabel>
                    <StatNumber 
                      fontSize="3xl" 
                      color={getPassRateColor(passRate)}
                      fontWeight="bold"
                    >
                      {passRate}%
                    </StatNumber>
                    <StatHelpText fontSize="xs">
                      {passedTests}/{totalTests} passed
                    </StatHelpText>
                  </Stat>
                </CardBody>
              </Card>

              {/* Duration */}
              <Card boxShadow="lg" _hover={{ transform: "translateY(-4px)", transition: "all 0.2s" }}>
                <CardBody>
                  <Stat>
                    <StatLabel fontSize="xs" color="gray.600">Duration</StatLabel>
                    <StatNumber fontSize="3xl" color="blue.600" fontWeight="bold">
                      {durationMin}m
                    </StatNumber>
                    <StatHelpText fontSize="xs">Total Time</StatHelpText>
                  </Stat>
                </CardBody>
              </Card>
            </SimpleGrid>
          </Box>

          <Divider />

          {/* Pipeline Status */}
          <Box>
            <Heading size="md" mb="4" color="gray.700">
             <Icon as={MdRefresh} mb="-1px" mr="1" /> Pipeline Stages
            </Heading>
            <SimpleGrid columns={{ base: 2, md: 4 }} spacing="4">
              {/* Discovery */}
              <Card 
                bg={isRecorder ? "purple.50" : discoveryOk ? "green.50" : "red.50"}
                borderLeft="4px"
                borderColor={isRecorder ? "purple.500" : discoveryOk ? "green.500" : "red.500"}
                boxShadow="md"
                _hover={{ transform: "translateY(-2px)", transition: "all 0.2s" }}
              >
                <CardBody>
                  <HStack justify="space-between" mb="2">
                    <Text fontWeight="bold" fontSize="md">Discovery</Text>
                    {isRecorder ? (
                      <Badge colorScheme="purple" fontSize="xs">SKIPPED</Badge>
                    ) : (
                      <Icon 
                        as={discoveryOk ? MdCheckCircle : MdCancel} 
                        boxSize="6" 
                        color={discoveryOk ? "green.500" : "red.500"} 
                      />
                    )}
                  </HStack>
                  <Text fontSize="sm" color="gray.700" fontWeight="medium">
                    {isRecorder ? "Manual Recording" : `${pagesCount} pages found`}
                  </Text>
                  <Text fontSize="xs" color="gray.600" mt="1">
                    {isRecorder ? "Recorder mode" : `${elementsCount} elements`}
                  </Text>
                </CardBody>
              </Card>

              {/* Test Generation */}
              <Card 
                bg={isRecorder ? "purple.50" : testsOk ? "green.50" : "red.50"}
                borderLeft="4px"
                borderColor={isRecorder ? "purple.500" : testsOk ? "green.500" : "red.500"}
                boxShadow="md"
                _hover={{ transform: "translateY(-2px)", transition: "all 0.2s" }}
              >
                <CardBody>
                  <HStack justify="space-between" mb="2">
                    <Text fontWeight="bold" fontSize="md">Generation</Text>
                    {isRecorder ? (
                      <Badge colorScheme="purple" fontSize="xs">SKIPPED</Badge>
                    ) : (
                      <Icon 
                        as={testsOk ? MdCheckCircle : MdCancel} 
                        boxSize="6" 
                        color={testsOk ? "green.500" : "red.500"} 
                      />
                    )}
                  </HStack>
                  <Text fontSize="sm" color="gray.700" fontWeight="medium">
                    {isRecorder ? "User recorded" : `${testsCount} tests created`}
                  </Text>
                  <Text fontSize="xs" color="gray.600" mt="1">
                    {isRecorder ? "Manual test" : `${testsData.metadata?.model || "stub"} model`}
                  </Text>
                </CardBody>
              </Card>

              {/* Execution */}
              <Card 
                bg={resultsOk ? "green.50" : "red.50"}
                borderLeft="4px"
                borderColor={resultsOk ? "green.500" : "red.500"}
                boxShadow="md"
                _hover={{ transform: "translateY(-2px)", transition: "all 0.2s" }}
              >
                <CardBody>
                  <HStack justify="space-between" mb="2">
                    <Text fontWeight="bold" fontSize="md">Execution</Text>
                    <Icon 
                      as={resultsOk ? MdCheckCircle : MdCancel} 
                      boxSize="6" 
                      color={resultsOk ? "green.500" : "red.500"} 
                    />
                  </HStack>
                  <Text fontSize="sm" color="gray.700" fontWeight="medium">
                    {passedTests}/{totalTests} passed
                  </Text>
                  <Text fontSize="xs" color="gray.600" mt="1">
                    {isHeaded ? "Visible browser" : `Exit code: ${exitCode}`}
                  </Text>
                </CardBody>
              </Card>

              {/* Healing */}
              <Card 
                bg="gray.50"
                borderLeft="4px"
                borderColor="gray.400"
                boxShadow="md"
                _hover={{ transform: "translateY(-2px)", transition: "all 0.2s" }}
              >
                <CardBody>
                  <HStack justify="space-between" mb="2">
                    <Text fontWeight="bold" fontSize="md">Healing</Text>
                    <Badge colorScheme="gray" fontSize="sm">
                      N/A
                    </Badge>
                  </HStack>
                  <Text fontSize="sm" color="gray.700" fontWeight="medium">
                    {healingOk ? "Available" : "Not needed"}
                  </Text>
                  <Text fontSize="xs" color="gray.600" mt="1">
                    Self-healing
                  </Text>
                </CardBody>
              </Card>
            </SimpleGrid>
          </Box>

          {/* Action Buttons */}
          <Divider />
          <HStack justify="center" spacing="4" pt="4">
            <Button
              size="lg"
              colorScheme="purple"
              onClick={() => navigate("/admin/runs")}
              px="8"
            >
              ← Back to Dashboard
            </Button>
            <Button
              size="lg"
              colorScheme="green"
              variant="outline"
              onClick={() => window.print()}
              px="8"
            >
              🖨️ Print Report
            </Button>
          </HStack>
        </VStack>
      </Box>
    </Fade>
  );
}