// ui/src/views/agentic/ResultsView.jsx
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
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Progress,
  Accordion,
  AccordionItem,
  AccordionButton,
  AccordionPanel,
  AccordionIcon,
  Button,
} from "@chakra-ui/react";
import { useParams, useNavigate } from "react-router-dom";
import axios from "axios";

const API = process.env.REACT_APP_API_BASE || "http://localhost:8000";

export default function ResultsView() {
  const { runId } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [resultsData, setResultsData] = useState(null);

  useEffect(() => {
    loadResults();
  }, [runId]);

  async function loadResults() {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.get(`${API}/api/run/${runId}/results`);
      if (res.data.ok) {
        setResultsData(res.data);
      } else {
        setError(res.data.message || "Results not yet available");
      }
    } catch (e) {
      console.error("Failed to load results:", e);
      setError(e.response?.data?.detail || e.message || "Failed to load results");
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <Box p="6" textAlign="center">
        <Spinner size="xl" color="blue.500" thickness="4px" mb="4" />
        <Text color="gray.600">Loading test results...</Text>
      </Box>
    );
  }

  if (error) {
    return (
      <Box p="6">
        <Alert status="warning" rounded="md">
          <AlertIcon />
          <Box>
            <AlertTitle>Results Not Available</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Box>
        </Alert>
        <Button mt="4" onClick={() => navigate("/admin/runs")}>
          Back to Dashboard
        </Button>
      </Box>
    );
  }

  if (!resultsData) {
    return (
      <Box p="6">
        <Alert status="info" rounded="md">
          <AlertIcon />
          No results data available
        </Alert>
        <Button mt="4" onClick={() => navigate("/admin/runs")}>
          Back to Dashboard
        </Button>
      </Box>
    );
  }

  const { summary = {}, tests = [], exitCode } = resultsData;
  const passRate = summary.total > 0 
    ? ((summary.passed / summary.total) * 100).toFixed(1)
    : 0;

  return (
    <Box p="6">
      <VStack align="stretch" spacing="6">
        {/* Header */}
        <HStack justify="space-between" align="start">
          <Box>
            <Heading size="lg" mb="2">
              Test Execution Results
            </Heading>
            <Text color="gray.600">
              Detailed results from test execution
            </Text>
          </Box>
          <Button size="sm" onClick={() => navigate("/admin/runs")}>
            Back to Dashboard
          </Button>
        </HStack>

        {/* Overall Status */}
        <Alert 
          status={exitCode === 0 ? "success" : "error"} 
          rounded="md"
          variant="left-accent"
        >
          <AlertIcon />
          <Box>
            <AlertTitle fontSize="md">
              {exitCode === 0 ? "✅ All Tests Passed" : "❌ Some Tests Failed"}
            </AlertTitle>
            <AlertDescription fontSize="sm">
              Exit Code: {exitCode} | Pass Rate: {passRate}%
            </AlertDescription>
          </Box>
        </Alert>

        {/* Summary Stats */}
        <SimpleGrid columns={{ base: 2, md: 4 }} spacing="4">
          <Card>
            <CardBody>
              <Stat>
                <StatLabel>Total Tests</StatLabel>
                <StatNumber color="blue.600">{summary.total || 0}</StatNumber>
              </Stat>
            </CardBody>
          </Card>

          <Card>
            <CardBody>
              <Stat>
                <StatLabel>Passed</StatLabel>
                <StatNumber color="green.600">{summary.passed || 0}</StatNumber>
                <StatHelpText>
                  {summary.total > 0 ? `${passRate}%` : "0%"}
                </StatHelpText>
              </Stat>
            </CardBody>
          </Card>

          <Card>
            <CardBody>
              <Stat>
                <StatLabel>Failed</StatLabel>
                <StatNumber color="red.600">{summary.failed || 0}</StatNumber>
              </Stat>
            </CardBody>
          </Card>

          <Card>
            <CardBody>
              <Stat>
                <StatLabel>Duration</StatLabel>
                <StatNumber color="purple.600">
                  {(summary.duration || 0).toFixed(2)}s
                </StatNumber>
              </Stat>
            </CardBody>
          </Card>
        </SimpleGrid>

        {/* Pass Rate Progress Bar */}
        <Box>
          <HStack justify="space-between" mb="2">
            <Text fontSize="sm" fontWeight="semibold">Pass Rate</Text>
            <Text fontSize="sm" fontWeight="bold" color={passRate >= 80 ? "green.600" : passRate >= 50 ? "orange.600" : "red.600"}>
              {passRate}%
            </Text>
          </HStack>
          <Progress 
            value={parseFloat(passRate)} 
            colorScheme={passRate >= 80 ? "green" : passRate >= 50 ? "orange" : "red"}
            size="lg"
            rounded="md"
            hasStripe
            isAnimated
          />
        </Box>

        {/* Test Results Table */}
        <Box>
          <Heading size="md" mb="4">
            Individual Test Results ({tests.length})
          </Heading>

          {tests.length === 0 ? (
            <Alert status="info" rounded="md">
              <AlertIcon />
              No test results available
            </Alert>
          ) : (
            <Box overflowX="auto" bg="white" rounded="md" border="1px" borderColor="gray.200">
              <Table variant="simple" size="sm">
                <Thead bg="gray.100">
                  <Tr>
                    <Th width="50px">#</Th>
                    <Th>Test Name</Th>
                    <Th width="100px">Status</Th>
                    <Th width="100px">Duration</Th>
                    <Th width="80px">Details</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {tests.map((test, idx) => (
                    <TestResultRow key={idx} test={test} index={idx} />
                  ))}
                </Tbody>
              </Table>
            </Box>
          )}
        </Box>

        {/* Failed Tests Details */}
        {summary.failed > 0 && (
          <Box>
            <Heading size="md" mb="4" color="red.600">
              Failed Tests Details
            </Heading>
            <Accordion allowMultiple>
              {tests
                .filter(t => t.outcome === "failed")
                .map((test, idx) => (
                  <AccordionItem key={idx} border="1px" borderColor="red.200" rounded="md" mb="2">
                    <AccordionButton py="3" _hover={{ bg: "red.50" }}>
                      <Box flex="1" textAlign="left">
                        <HStack spacing="2">
                          <Badge colorScheme="red">Failed</Badge>
                          <Text fontSize="sm" fontWeight="semibold" fontFamily="monospace">
                            {test.nodeid}
                          </Text>
                        </HStack>
                      </Box>
                      <AccordionIcon />
                    </AccordionButton>
                    <AccordionPanel pb="4" bg="red.50">
                      <VStack align="stretch" spacing="2">
                        <Box>
                          <Text fontSize="xs" fontWeight="semibold" color="gray.700" mb="1">
                            Error Message:
                          </Text>
                          <Box
                            bg="gray.900"
                            color="red.300"
                            p="3"
                            rounded="md"
                            fontSize="xs"
                            fontFamily="monospace"
                            whiteSpace="pre-wrap"
                            maxH="200px"
                            overflowY="auto"
                          >
                            {test.error || "No error details available"}
                          </Box>
                        </Box>
                        <HStack fontSize="xs" color="gray.600">
                          <Text>Duration: {test.duration?.toFixed(2)}s</Text>
                        </HStack>
                      </VStack>
                    </AccordionPanel>
                  </AccordionItem>
                ))}
            </Accordion>
          </Box>
        )}
      </VStack>
    </Box>
  );
}

// Individual test result row
function TestResultRow({ test, index }) {
  const getOutcomeColor = (outcome) => {
    switch(outcome) {
      case "passed": return "green";
      case "failed": return "red";
      case "skipped": return "yellow";
      default: return "gray";
    }
  };

  const getOutcomeIcon = (outcome) => {
    switch(outcome) {
      case "passed": return "✓";
      case "failed": return "✗";
      case "skipped": return "⊘";
      default: return "?";
    }
  };

  return (
    <Tr _hover={{ bg: "gray.50" }}>
      <Td fontWeight="medium" color="gray.600">{index + 1}</Td>
      <Td>
        <Text fontSize="sm" fontFamily="monospace" isTruncated maxW="400px" title={test.nodeid}>
          {test.nodeid}
        </Text>
      </Td>
      <Td>
        <Badge colorScheme={getOutcomeColor(test.outcome)} fontSize="xs">
          {getOutcomeIcon(test.outcome)} {test.outcome}
        </Badge>
      </Td>
      <Td>
        <Text fontSize="sm" fontFamily="monospace">
          {test.duration?.toFixed(2)}s
        </Text>
      </Td>
      <Td>
        {test.error && (
          <Badge colorScheme="red" fontSize="xs">
            Has Error
          </Badge>
        )}
      </Td>
    </Tr>
  );
}