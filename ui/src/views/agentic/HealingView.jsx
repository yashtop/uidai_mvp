// ui/src/views/agentic/HealingView.jsx - WITH BEFORE/AFTER COMPARISON

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
  Accordion,
  AccordionItem,
  AccordionButton,
  AccordionPanel,
  AccordionIcon,
  Button,
  Icon,
  Divider,
  Code,
  useColorModeValue,
  Progress,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Fade,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  Tooltip,
  Grid,
  GridItem,
} from "@chakra-ui/react";
import { useParams, useNavigate } from "react-router-dom";
import { 
  MdAutoFixHigh, 
  MdCheckCircle, 
  MdWarning,
  MdRefresh,
  MdCode,
  MdBugReport,
  MdCompareArrows,
  MdError,
  MdTimeline,
  MdInfo,
  MdPsychology,
} from "react-icons/md";
import axios from "axios";

const API = process.env.REACT_APP_API_BASE || "http://localhost:8000";

export default function HealingView() {
  const { runId } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [healingData, setHealingData] = useState(null);

  const bgCard = useColorModeValue("white", "gray.800");
  const bgCode = useColorModeValue("gray.50", "gray.900");
  const textColor = useColorModeValue("gray.900", "white");
  const textColorSecondary = useColorModeValue("gray.600", "gray.400");
  const borderColor = useColorModeValue("gray.200", "gray.700");

  useEffect(() => {
    loadHealing();
  }, [runId]);

  async function loadHealing() {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.get(`${API}/api/run/${runId}/healing`);
      console.log("Healing data:", res.data);
      
      if (res.data.ok !== false) {
        setHealingData(res.data);
      } else {
        setError(res.data.message || "Healing data not available");
      }
    } catch (e) {
      console.error("Failed to load healing:", e);
      setError(e.response?.data?.detail || e.message || "Failed to load healing data");
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <Box p="6" textAlign="center">
        <Spinner size="xl" color="blue.500" thickness="4px" mb="4" />
        <Text color={textColorSecondary}>Loading healing data...</Text>
      </Box>
    );
  }

  if (error) {
    return (
      <Box p="6">
        <Alert status="info" rounded="md">
          <AlertIcon />
          <Box>
            <AlertTitle>Healing Data Not Available</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Box>
        </Alert>
        <Button mt="4" onClick={() => navigate("/admin/runs")}>
          Back to Dashboard
        </Button>
      </Box>
    );
  }

  if (!healingData || !healingData.attempts || healingData.attempts.length === 0) {
    return (
      <Box p="6">
        <Alert status="success" rounded="md">
          <AlertIcon />
          <Box>
            <AlertTitle>✅ No Healing Needed</AlertTitle>
            <AlertDescription>
              All tests passed on the first attempt! No auto-healing was required.
            </AlertDescription>
          </Box>
        </Alert>
        <Button mt="4" onClick={() => navigate("/admin/runs")}>
          Back to Dashboard
        </Button>
      </Box>
    );
  }

  const { attempts = [], healed, healing_attempts = 0, final_result = {} } = healingData;
  const totalAttempts = attempts.length;
  const successRate = healed ? 100 : 0;
  const finalPassed = final_result.summary?.passed || 0;
  const finalTotal = final_result.summary?.total || 0;
  const finalFailed = final_result.summary?.failed || 0;

  return (
    <Fade in={true}>
      <Box p="6" maxW="1800px" mx="auto">
        <VStack align="stretch" spacing="6">
          {/* Header */}
          <HStack justify="space-between" align="start">
            <Box>
              <Heading size="lg" mb="2" color={textColor}>
                <Icon as={MdAutoFixHigh} mr="2" mb="-1px" color="blue.500" />
                Auto-Healing Report
              </Heading>
              <Text color={textColorSecondary}>
                Complete before/after code comparison with AI analysis
              </Text>
            </Box>
            <HStack spacing="2">
              <Button size="sm" variant="outline" onClick={loadHealing}>
                <Icon as={MdRefresh} mr="1" /> Refresh
              </Button>
              <Button size="sm" onClick={() => navigate("/admin/runs")}>
                Back
              </Button>
            </HStack>
          </HStack>

          {/* Status Banner */}
          <Alert 
            status={healed ? "success" : "warning"} 
            rounded="xl"
            variant="left-accent"
            boxShadow="lg"
          >
            <AlertIcon boxSize="6" />
            <Box flex="1">
              <AlertTitle fontSize="xl" fontWeight="bold">
                {healed ? "✅ Tests Successfully Healed" : "⚠️ Healing Incomplete"}
              </AlertTitle>
              <AlertDescription fontSize="sm" mt="2">
                {healed 
                  ? `All test failures were automatically fixed after ${healing_attempts} healing attempt(s). AI rewrote the failing tests to pass.`
                  : `Completed ${totalAttempts} healing attempt(s). Some tests still require manual attention.`}
              </AlertDescription>
            </Box>
          </Alert>

          {/* Summary Stats */}
          <SimpleGrid columns={{ base: 2, md: 5 }} spacing="4">
            <Card bg={bgCard} boxShadow="lg" borderTop="4px solid" borderColor="blue.500">
              <CardBody>
                <Stat>
                  <StatLabel fontSize="xs">Total Attempts</StatLabel>
                  <StatNumber fontSize="3xl" color="blue.600">{totalAttempts}</StatNumber>
                  <StatHelpText fontSize="xs">Healing cycles</StatHelpText>
                </Stat>
              </CardBody>
            </Card>

            <Card bg={bgCard} boxShadow="lg" borderTop="4px solid" borderColor="green.500">
              <CardBody>
                <Stat>
                  <StatLabel fontSize="xs">Success Rate</StatLabel>
                  <StatNumber fontSize="3xl" color={healed ? "green.600" : "orange.600"}>
                    {successRate}%
                  </StatNumber>
                  <StatHelpText fontSize="xs">{healed ? "Fully resolved" : "Partial"}</StatHelpText>
                </Stat>
              </CardBody>
            </Card>

            <Card bg={bgCard} boxShadow="lg" borderTop="4px solid" borderColor="purple.500">
              <CardBody>
                <Stat>
                  <StatLabel fontSize="xs">Tests Fixed</StatLabel>
                  <StatNumber fontSize="3xl" color="purple.600">{finalPassed}</StatNumber>
                  <StatHelpText fontSize="xs">of {finalTotal} total</StatHelpText>
                </Stat>
              </CardBody>
            </Card>

            <Card bg={bgCard} boxShadow="lg" borderTop="4px solid" borderColor="orange.500">
              <CardBody>
                <Stat>
                  <StatLabel fontSize="xs">Final Status</StatLabel>
                  <StatNumber fontSize="2xl" color={healed ? "green.600" : "red.600"}>
                    {healed ? <Icon as={MdCheckCircle} boxSize="8" /> : <Icon as={MdWarning} boxSize="8" />}
                  </StatNumber>
                </Stat>
              </CardBody>
            </Card>

            <Card bg={bgCard} boxShadow="lg" borderTop="4px solid" borderColor="red.500">
              <CardBody>
                <Stat>
                  <StatLabel fontSize="xs">Remaining Issues</StatLabel>
                  <StatNumber fontSize="3xl" color="red.600">{finalFailed}</StatNumber>
                  <StatHelpText fontSize="xs">Still failing</StatHelpText>
                </Stat>
              </CardBody>
            </Card>
          </SimpleGrid>

          {/* Progress */}
          <Card bg={bgCard} boxShadow="md">
            <CardBody>
              <HStack justify="space-between" mb="3">
                <Text fontSize="md" fontWeight="bold">
                  <Icon as={MdTimeline} mr="2" mb="-1px" />
                  Healing Progress
                </Text>
                <Badge colorScheme={healed ? "green" : "orange"} fontSize="md" px="3" py="1">
                  {healed ? "✓ Complete" : "⚠ Incomplete"}
                </Badge>
              </HStack>
              <Progress 
                value={successRate} 
                colorScheme={healed ? "green" : "orange"}
                size="lg"
                rounded="md"
                hasStripe
                isAnimated
              />
            </CardBody>
          </Card>

          <Divider />

          {/* Detailed Attempts */}
          <Box>
            <Heading size="md" mb="4">
              <Icon as={MdBugReport} mr="2" mb="-1px" />
              Healing Attempts Timeline ({totalAttempts})
            </Heading>

            <Accordion allowMultiple defaultIndex={[0]}>
              {attempts.map((attempt, idx) => {
                const attemptNum = attempt.attempt || (idx + 1);
                const summary = attempt.summary || {};
                const passed = summary.passed || 0;
                const failed = summary.failed || 0;
                const total = summary.total || 0;
                
                // Get code from API
                const appliedFix = attempt.applied_fix || {};
                const originalCode = appliedFix.original_code || null;  // Will be null until backend updated
                const fixedCode = appliedFix.fix || appliedFix.fixed_code || "";
                const issue = appliedFix.issue || "Test failure";
                const confidence = appliedFix.confidence || 0;
                
                // Check if we have both codes for comparison
                const hasComparison = originalCode && fixedCode;
                
                // Get error from test stdout
                const testResult = attempt.result?.tests?.[0] || {};
                const errorOutput = testResult.call?.stdout || "";
                
                // Get healing suggestions
                const healingSuggestions = attempt.healing?.suggestions || [];
                const aiModel = attempt.healing?.fromModel || "AI";
                
                const isSuccess = failed === 0 && total > 0;
                
                return (
                  <AccordionItem key={idx} border="1px" borderColor={borderColor} rounded="lg" mb="3">
                    <h2>
                      <AccordionButton 
                        _expanded={{ bg: isSuccess ? "green.50" : "orange.50" }}
                        rounded="lg"
                        py="4"
                      >
                        <Box flex="1" textAlign="left">
                          <HStack spacing="3">
                            <Badge colorScheme={isSuccess ? "green" : "orange"} fontSize="lg" px="4" py="2" rounded="full">
                              Attempt #{attemptNum}
                            </Badge>
                            <VStack align="start" spacing="0">
                              <HStack spacing="2">
                                <Badge colorScheme="green">{passed} passed</Badge>
                                <Badge colorScheme="red">{failed} failed</Badge>
                                <Badge colorScheme="gray">{total} total</Badge>
                              </HStack>
                              {isSuccess && (
                                <HStack mt="1">
                                  <Icon as={MdCheckCircle} color="green.500" boxSize="4" />
                                  <Text fontSize="xs" color="green.600" fontWeight="bold">
                                    All passed after AI fix!
                                  </Text>
                                </HStack>
                              )}
                            </VStack>
                          </HStack>
                        </Box>
                        <AccordionIcon boxSize="6" />
                      </AccordionButton>
                    </h2>
                    <AccordionPanel pb="6" pt="4">
                      <VStack align="stretch" spacing="5">
                        {/* AI Model Info */}
                        <Card bg="purple.50" borderLeft="4px" borderColor="purple.500">
                          <CardBody>
                            <HStack justify="space-between">
                              <HStack>
                                <Icon as={MdPsychology} color="purple.500" boxSize="5" />
                                <Heading size="sm" color="purple.700">AI Model Used</Heading>
                              </HStack>
                              <Badge colorScheme="purple" fontSize="md" px="3" py="1">
                                {aiModel}
                              </Badge>
                            </HStack>
                            <Text fontSize="xs" color="purple.600" mt="2">
                              Confidence: {Math.round(confidence * 100)}%
                            </Text>
                          </CardBody>
                        </Card>

                        {/* Original Error */}
                        {errorOutput && (
                          <Card bg="red.50" borderLeft="4px" borderColor="red.500">
                            <CardBody>
                              <HStack mb="2">
                                <Icon as={MdError} color="red.500" boxSize="5" />
                                <Heading size="sm" color="red.700">Original Test Error</Heading>
                              </HStack>
                              <Code 
                                display="block" 
                                whiteSpace="pre-wrap" 
                                p="3" 
                                rounded="md" 
                                bg="white" 
                                fontSize="xs"
                                color="red.700"
                                fontFamily="monospace"
                                maxH="200px"
                                overflowY="auto"
                              >
                                {errorOutput}
                              </Code>
                            </CardBody>
                          </Card>
                        )}

                        {/* Issue Description */}
                        <Card bg="orange.50" borderLeft="4px" borderColor="orange.500">
                          <CardBody>
                            <HStack mb="2">
                              <Icon as={MdWarning} color="orange.500" boxSize="5" />
                              <Heading size="sm" color="orange.700">Identified Issue</Heading>
                            </HStack>
                            <Text fontSize="sm" color="orange.800">
                              {issue}
                            </Text>
                          </CardBody>
                        </Card>

                        {/* AI Suggestions */}
                        {healingSuggestions.length > 0 && (
                          <Card bg="blue.50" borderLeft="4px" borderColor="blue.500">
                            <CardBody>
                              <HStack mb="3">
                                <Icon as={MdAutoFixHigh} color="blue.500" boxSize="5" />
                                <Heading size="sm" color="blue.700">
                                  AI Healing Suggestions ({healingSuggestions.length})
                                </Heading>
                              </HStack>
                              <VStack align="stretch" spacing="2">
                                {healingSuggestions.map((suggestion, sIdx) => (
                                  <Box key={sIdx} p="3" bg="white" rounded="md">
                                    <HStack justify="space-between" mb="1">
                                      <Badge colorScheme="blue">{suggestion.priority || "medium"} priority</Badge>
                                      <Badge colorScheme="green">{Math.round((suggestion.confidence || 0) * 100)}% confident</Badge>
                                    </HStack>
                                    <Text fontSize="xs" color="blue.800" fontWeight="bold" mt="1">
                                      Issue: {suggestion.issue}
                                    </Text>
                                  </Box>
                                ))}
                              </VStack>
                            </CardBody>
                          </Card>
                        )}

                        {/* Code Comparison - Side by Side OR Single View */}
                        {hasComparison ? (
                          // SIDE-BY-SIDE COMPARISON (when backend provides original_code)
                          <Card bg={bgCard} boxShadow="md">
                            <CardBody>
                              <HStack mb="4">
                                <Icon as={MdCompareArrows} color="purple.500" boxSize="6" />
                                <Heading size="sm">Before/After Code Comparison</Heading>
                              </HStack>

                              <Grid
  templateColumns="repeat(2, 1fr)"
  gap={4}
  overflowX="auto"        // ✅ enable horizontal scroll if boxes overflow
  whiteSpace="nowrap"     // ensures boxes stay side-by-side and scrollable
>
  {/* BEFORE (Original) */}
  <GridItem minW="600px"> {/* ✅ fix width so both boxes fit horizontally */}
    <Box
      bg={bgCode}
      p="4"
      rounded="md"
      border="2px"
      borderColor="red.300"
      maxH="600px"
      overflowY="auto"
      overflowX="auto"    // ✅ allow horizontal scrolling within the box
    >
      <HStack justify="space-between" mb="3">
        <Badge colorScheme="red" fontSize="md">
          ❌ BEFORE (Original Test)
        </Badge>
        <Tooltip label="Copy original code">
          <Button
            size="xs"
            onClick={() => navigator.clipboard.writeText(originalCode)}
          >
            Copy
          </Button>
        </Tooltip>
      </HStack>
      <Code
        display="block"
        whiteSpace="pre"
        fontSize="xs"
        fontFamily="monospace"
        bg="transparent"
        p="0"
        lineHeight="1.6"
      >
        {originalCode}
      </Code>
    </Box>
  </GridItem>

  {/* AFTER (Fixed) */}
  <GridItem minW="600px">
    <Box
      bg={bgCode}
      p="4"
      rounded="md"
      border="2px"
      borderColor="green.300"
      maxH="600px"
      overflowY="auto"
      overflowX="auto"    // ✅ horizontal scroll if long lines
    >
      <HStack justify="space-between" mb="3">
        <Badge colorScheme="green" fontSize="md">
          ✅ AFTER (AI Fixed)
        </Badge>
        <Tooltip label="Copy fixed code">
          <Button
            size="xs"
            onClick={() => navigator.clipboard.writeText(fixedCode)}
          >
            Copy
          </Button>
        </Tooltip>
      </HStack>
      <Code
        display="block"
        whiteSpace="pre"
        fontSize="xs"
        fontFamily="monospace"
        bg="transparent"
        p="0"
        lineHeight="1.6"
      >
        {fixedCode}
      </Code>
    </Box>
  </GridItem>
</Grid>

                              <Alert status="success" mt="4" rounded="md">
                                <AlertIcon />
                                <Text fontSize="xs">
                                  Compare the original failing test (left) with the AI-healed version (right)
                                </Text>
                              </Alert>
                            </CardBody>
                          </Card>
                        ) : (
                          // SINGLE VIEW (current - only fixed code available)
                          <Card bg={bgCard} boxShadow="md">
                            <CardBody>
                              <HStack mb="4">
                                <Icon as={MdCode} color="green.500" boxSize="6" />
                                <Heading size="sm">AI-Generated Fixed Test Code</Heading>
                              </HStack>

                              <Box 
                                bg={bgCode} 
                                p="4" 
                                rounded="md" 
                                border="2px" 
                                borderColor="green.200"
                                maxH="500px"
                                overflowY="auto"
                              >
                                <HStack justify="space-between" mb="3">
                                  <Badge colorScheme="green" fontSize="md">
                                    ✅ Fixed Test Code (Applied)
                                  </Badge>
                                  <Tooltip label="Copy to clipboard">
                                    <Button 
                                      size="xs" 
                                      onClick={() => navigator.clipboard.writeText(fixedCode)}
                                    >
                                      Copy
                                    </Button>
                                  </Tooltip>
                                </HStack>
                                <Code 
                                  display="block" 
                                  whiteSpace="pre" 
                                  fontSize="xs"
                                  fontFamily="monospace"
                                  bg="transparent"
                                  p="0"
                                  lineHeight="1.6"
                                >
                                  {fixedCode}
                                </Code>
                              </Box>

                              <Alert status="info" mt="3" rounded="md">
                                <AlertIcon />
                                <Box>
                                  <AlertTitle fontSize="xs">Original Code Not Available</AlertTitle>
                                  <AlertDescription fontSize="xs">
                                    Update your backend to store original_code in applied_fix to see before/after comparison.
                                  </AlertDescription>
                                </Box>
                              </Alert>
                            </CardBody>
                          </Card>
                        )}

                        {/* Test Execution Results */}
                        {attempt.result?.tests && attempt.result.tests.length > 0 && (
                          <Card bg={bgCard} boxShadow="md">
                            <CardBody>
                              <Heading size="sm" mb="3">Test Execution Results</Heading>
                              <Box overflowX="auto">
                                <Table variant="simple" size="sm">
                                  <Thead>
                                    <Tr>
                                      <Th>Test Name</Th>
                                      <Th>Status</Th>
                                      <Th>Duration</Th>
                                      <Th>Line</Th>
                                    </Tr>
                                  </Thead>
                                  <Tbody>
                                    {attempt.result.tests.map((test, testIdx) => (
                                      <Tr key={testIdx}>
                                        <Td fontSize="xs" fontFamily="monospace" maxW="300px" isTruncated>
                                          {test.nodeid || "Unknown"}
                                        </Td>
                                        <Td>
                                          <Badge colorScheme={test.outcome === "passed" ? "green" : "red"} fontSize="xs">
                                            {test.outcome || "unknown"}
                                          </Badge>
                                        </Td>
                                        <Td fontSize="xs">
                                          {test.call?.duration ? `${test.call.duration.toFixed(2)}s` : "N/A"}
                                        </Td>
                                        <Td fontSize="xs">
                                          {test.lineno || "-"}
                                        </Td>
                                      </Tr>
                                    ))}
                                  </Tbody>
                                </Table>
                              </Box>
                            </CardBody>
                          </Card>
                        )}

                        {/* Artifacts */}
                        {attempt.result?.artifacts && attempt.result.artifacts.length > 0 && (
                          <Card bg="gray.50" borderLeft="4px" borderColor="gray.400">
                            <CardBody>
                              <Heading size="sm" mb="2">Generated Artifacts</Heading>
                              <VStack align="stretch" spacing="1">
                                {attempt.result.artifacts.map((artifact, aIdx) => (
                                  <Text key={aIdx} fontSize="xs" fontFamily="monospace" color="gray.600">
                                    📄 {artifact}
                                  </Text>
                                ))}
                              </VStack>
                            </CardBody>
                          </Card>
                        )}
                      </VStack>
                    </AccordionPanel>
                  </AccordionItem>
                );
              })}
            </Accordion>
          </Box>

          {/* Final Summary */}
          <Card bg={healed ? "green.50" : "orange.50"} boxShadow="lg">
            <CardBody>
              <HStack spacing="3" mb="3">
                <Icon as={healed ? MdCheckCircle : MdWarning} boxSize="8" color={healed ? "green.600" : "orange.600"} />
                <Box>
                  <Heading size="md" color={healed ? "green.700" : "orange.700"}>
                    Final Outcome
                  </Heading>
                  <Text fontSize="sm" color={healed ? "green.600" : "orange.600"} mt="1">
                    {healed 
                      ? "AI successfully rewrote and fixed all failing tests"
                      : "Some tests still require manual attention after AI healing"}
                  </Text>
                </Box>
              </HStack>

              <Divider my="3" />

              <SimpleGrid columns={{ base: 1, md: 3 }} spacing="3">
                <Box>
                  <Text fontSize="xs" color={textColorSecondary} fontWeight="bold">Total Healing Cycles</Text>
                  <Text fontSize="2xl" fontWeight="bold">{totalAttempts}</Text>
                </Box>
                <Box>
                  <Text fontSize="xs" color={textColorSecondary} fontWeight="bold">Final Pass Rate</Text>
                  <Text fontSize="2xl" fontWeight="bold" color={healed ? "green.600" : "orange.600"}>
                    {finalTotal > 0 ? Math.round((finalPassed / finalTotal) * 100) : 0}%
                  </Text>
                </Box>
                <Box>
                  <Text fontSize="xs" color={textColorSecondary} fontWeight="bold">Final Tests Status</Text>
                  <HStack spacing="2" mt="1">
                    <Badge colorScheme="green" fontSize="md">{finalPassed} passed</Badge>
                    <Badge colorScheme="red" fontSize="md">{finalFailed} failed</Badge>
                  </HStack>
                </Box>
              </SimpleGrid>
            </CardBody>
          </Card>

          {/* Action Buttons */}
          <HStack justify="center" spacing="4">
            <Button 
              colorScheme="blue" 
              onClick={() => navigate(`/admin/run/${runId}/report`)}
              leftIcon={<Icon as={MdCode} />}
            >
              View Full Report
            </Button>
            <Button 
              variant="outline" 
              onClick={() => window.print()}
            >
              Print Healing Report
            </Button>
          </HStack>
        </VStack>
      </Box>
    </Fade>
  );
}
