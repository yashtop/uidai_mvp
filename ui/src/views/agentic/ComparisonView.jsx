// ui/src/views/agentic/ComparisonView.jsx - MATCHES YOUR API

import React, { useState, useEffect } from "react";
import {
  Box,
  Heading,
  Text,
  VStack,
  HStack,
  Button,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Badge,
  Card,
  CardBody,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  SimpleGrid,
  Alert,
  AlertIcon,
  Icon,
  Spinner,
  useColorModeValue,
  Checkbox,
} from "@chakra-ui/react";
import { MdCompare, MdCheckCircle, MdCancel, MdWarning } from "react-icons/md";
import { useNavigate } from "react-router-dom";
import axios from "axios";

const API = process.env.REACT_APP_API_BASE || "http://localhost:8000";

export default function ComparisonView() {
  const navigate = useNavigate();
  const [allRuns, setAllRuns] = useState([]);
  const [selectedRuns, setSelectedRuns] = useState([]);
  const [comparison, setComparison] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingRuns, setLoadingRuns] = useState(true);
  const [error, setError] = useState(null);

  const bgCard = useColorModeValue("white", "gray.800");
  const borderColor = useColorModeValue("gray.200", "gray.700");
  const selectedBg = useColorModeValue("purple.50", "purple.900");
  const hoverBg = useColorModeValue("gray.100", "gray.700");

  useEffect(() => {
    loadAllRuns();
  }, []);

  async function loadAllRuns() {
    setLoadingRuns(true);
    try {
      const res = await axios.get(`${API}/api/runs`);
      console.log("API Response:", res.data);
      
      // Map API response to expected format
      const runs = (res.data.runs || []).map(run => ({
        id: run.runId,  // Map runId to id
        target_url: run.targetUrl,  // Map camelCase to snake_case
        status: run.status,
        created_at: run.createdAt,
        completed_at: run.completedAt,
        preset: run.preset,
        mode: run.mode,
        phase: run.phase
      }));
      
      // Filter valid runs
      const validRuns = runs.filter(run => run.id && typeof run.id === 'string');
      
      console.log(`Loaded ${validRuns.length} valid runs of ${runs.length} total`);
      setAllRuns(validRuns);
    } catch (e) {
      console.error("Failed to load runs:", e);
      setError("Failed to load runs. Please try again.");
    } finally {
      setLoadingRuns(false);
    }
  }

  async function handleCompare() {
    if (selectedRuns.length < 2) {
      setError("Please select at least 2 runs to compare");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const runIds = selectedRuns.join(",");
      console.log("Comparing runs:", runIds);
      const res = await axios.get(`${API}/api/runs/compare?run_ids=${runIds}`);
      console.log("Comparison result:", res.data);
      setComparison(res.data);
    } catch (e) {
      console.error("Comparison error:", e);
      setError(e.response?.data?.detail || "Failed to compare runs");
    } finally {
      setLoading(false);
    }
  }

  function toggleSelectRun(runId, event) {
    if (event) {
      event.stopPropagation();
    }
    
    if (!runId) return;
    
    if (selectedRuns.includes(runId)) {
      setSelectedRuns(selectedRuns.filter((id) => id !== runId));
    } else {
      if (selectedRuns.length < 5) {
        setSelectedRuns([...selectedRuns, runId]);
      } else {
        setError("Maximum 5 runs can be compared at once");
      }
    }
  }

  function isSelected(runId) {
    return runId && selectedRuns.includes(runId);
  }

  const getPassRateColor = (rate) => {
    if (rate >= 80) return "green";
    if (rate >= 50) return "orange";
    return "red";
  };

  const formatDate = (dateString) => {
    if (!dateString) return "N/A";
    try {
      return new Date(dateString).toLocaleString();
    } catch (e) {
      return "Invalid Date";
    }
  };

  const getRunId = (run) => {
    if (!run || !run.id) return "unknown";
    return typeof run.id === 'string' ? run.id.slice(-8) : String(run.id).slice(-8);
  };

  if (loadingRuns) {
    return (
      <Box p="6" textAlign="center">
        <Spinner size="xl" color="purple.500" />
        <Text mt="4">Loading runs...</Text>
      </Box>
    );
  }

  return (
    <Box p="6" maxW="1400px" mx="auto">
      <VStack align="stretch" spacing="6">
        {/* Header */}
        <HStack justify="space-between">
          <Box>
            <Heading size="lg" mb="2">
              <Icon as={MdCompare} mr="2" />
              Test Run Comparison
            </Heading>
            <Text color="gray.600">
              Compare test runs side-by-side to track improvements
            </Text>
          </Box>
          <Button onClick={() => navigate("/admin/runs")} variant="ghost">
            ← Back
          </Button>
        </HStack>

        {/* Run Selection */}
        <Card bg={bgCard} shadow="md">
          <CardBody>
            <HStack justify="space-between" mb="4">
              <Heading size="md">
                Select Runs to Compare (2-5 runs)
              </Heading>
              <Badge colorScheme="purple" fontSize="md" px="3" py="1">
                {selectedRuns.length} selected
              </Badge>
            </HStack>

            {allRuns.length === 0 ? (
              <Alert status="info">
                <AlertIcon />
                No test runs available. Please run some tests first.
              </Alert>
            ) : (
              <VStack align="stretch" spacing="3" maxH="500px" overflowY="auto">
                {allRuns.map((run) => {
                  if (!run || !run.id) return null;
                  
                  return (
                    <HStack
                      key={run.id}
                      p="4"
                      bg={isSelected(run.id) ? selectedBg : "white"}
                      rounded="md"
                      cursor="pointer"
                      border="2px"
                      borderColor={isSelected(run.id) ? "purple.500" : borderColor}
                      _hover={{ bg: isSelected(run.id) ? selectedBg : hoverBg }}
                      transition="all 0.2s"
                      onClick={(e) => toggleSelectRun(run.id, e)}
                    >
                      {/* Checkbox */}
                      <Checkbox
                        isChecked={isSelected(run.id)}
                        onChange={(e) => toggleSelectRun(run.id, e)}
                        colorScheme="purple"
                        size="lg"
                        onClick={(e) => e.stopPropagation()}
                      />

                      {/* Run Info */}
                      <Box flex="1">
                        <HStack spacing="2" mb="1">
                          <Text fontWeight="bold" fontSize="sm" noOfLines={1}>
                            {run.target_url || "No URL"}
                          </Text>
                          <Badge colorScheme={run.status === "completed" ? "green" : run.status === "failed" ? "red" : "yellow"}>
                            {run.status || "unknown"}
                          </Badge>
                          {run.preset && (
                            <Badge colorScheme="blue" variant="outline">
                              {run.preset}
                            </Badge>
                          )}
                        </HStack>
                        <HStack spacing="3" fontSize="xs" color="gray.600">
                          <Text>ID: {getRunId(run)}</Text>
                          <Text>•</Text>
                          <Text>{formatDate(run.created_at)}</Text>
                        </HStack>
                      </Box>

                      {/* Checkmark icon */}
                      {isSelected(run.id) && (
                        <Icon as={MdCheckCircle} color="purple.500" boxSize="6" />
                      )}
                    </HStack>
                  );
                })}
              </VStack>
            )}

            <HStack mt="4" spacing="3">
              <Button
                colorScheme="purple"
                onClick={handleCompare}
                isLoading={loading}
                isDisabled={selectedRuns.length < 2}
                size="lg"
                leftIcon={<MdCompare />}
              >
                Compare {selectedRuns.length} Run{selectedRuns.length !== 1 ? "s" : ""}
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  setSelectedRuns([]);
                  setError(null);
                }}
                isDisabled={selectedRuns.length === 0}
              >
                Clear Selection
              </Button>
              <Button variant="ghost" onClick={loadAllRuns}>
                Refresh Runs
              </Button>
            </HStack>
          </CardBody>
        </Card>

        {/* Error */}
        {error && (
          <Alert status="error" rounded="md">
            <AlertIcon />
            {error}
          </Alert>
        )}

        {/* Comparison Results */}
        {comparison && (
          <>
            {/* Summary Cards */}
            <SimpleGrid columns={{ base: 1, md: 3 }} spacing="4">
              <Card>
                <CardBody>
                  <Stat>
                    <StatLabel>Average Pass Rate</StatLabel>
                    <StatNumber color={getPassRateColor(comparison.summary.avg_pass_rate) + ".500"}>
                      {comparison.summary.avg_pass_rate}%
                    </StatNumber>
                    <StatHelpText>Across {comparison.summary.total_runs} runs</StatHelpText>
                  </Stat>
                </CardBody>
              </Card>

              <Card>
                <CardBody>
                  <Stat>
                    <StatLabel>Average Duration</StatLabel>
                    <StatNumber>{(comparison.summary.avg_duration || 0).toFixed(1)}s</StatNumber>
                    <StatHelpText>Test execution time</StatHelpText>
                  </Stat>
                </CardBody>
              </Card>

              <Card>
                <CardBody>
                  <Stat>
                    <StatLabel>Common Failures</StatLabel>
                    <StatNumber>{(comparison.summary.common_failures || []).length}</StatNumber>
                    <StatHelpText>Tests failing in multiple runs</StatHelpText>
                  </Stat>
                </CardBody>
              </Card>
            </SimpleGrid>

            {/* Common Failures */}
            {comparison.summary.common_failures && comparison.summary.common_failures.length > 0 && (
              <Card bg="red.50" borderColor="red.200" borderWidth="2px">
                <CardBody>
                  <HStack mb="3">
                    <Icon as={MdWarning} color="red.500" boxSize="5" />
                    <Heading size="md">Common Failures (Flaky Tests)</Heading>
                  </HStack>
                  <Text fontSize="sm" color="gray.600" mb="3">
                    These tests failed in multiple runs and may be flaky
                  </Text>
                  <VStack align="stretch" spacing="2">
                    {comparison.summary.common_failures.map((failure, idx) => (
                      <HStack key={idx} p="3" bg="white" rounded="md" shadow="sm">
                        <Badge colorScheme="red" fontSize="md" px="2">
                          {failure.occurrences}x
                        </Badge>
                        <Text fontSize="sm" fontFamily="monospace" flex="1">
                          {failure.test}
                        </Text>
                      </HStack>
                    ))}
                  </VStack>
                </CardBody>
              </Card>
            )}

            {/* Comparison Table */}
            <Card>
              <CardBody>
                <Heading size="md" mb="4">
                  Side-by-Side Comparison
                </Heading>

                <Box overflowX="auto">
                  <Table variant="simple" size="sm">
                    <Thead>
                      <Tr>
                        <Th position="sticky" left="0" bg={bgCard} zIndex="1">
                          Metric
                        </Th>
                        {(comparison.runs || []).map((run, idx) => (
                          <Th key={idx}>
                            Run {idx + 1}
                            <br />
                            <Text fontSize="xs" fontWeight="normal" color="gray.500">
                              {run.run_id ? run.run_id.slice(-8) : "unknown"}
                            </Text>
                          </Th>
                        ))}
                      </Tr>
                    </Thead>
                    <Tbody>
                      {/* Status */}
                      <Tr>
                        <Td fontWeight="bold" position="sticky" left="0" bg={bgCard}>
                          Status
                        </Td>
                        {(comparison.runs || []).map((run, idx) => (
                          <Td key={idx}>
                            <Badge colorScheme={run.status === "completed" ? "green" : "red"}>
                              {run.status || "unknown"}
                            </Badge>
                          </Td>
                        ))}
                      </Tr>

                      {/* URL */}
                      <Tr>
                        <Td fontWeight="bold" position="sticky" left="0" bg={bgCard}>
                          Target URL
                        </Td>
                        {(comparison.runs || []).map((run, idx) => (
                          <Td key={idx}>
                            <Text fontSize="xs" noOfLines={2}>
                              {run.target_url || "N/A"}
                            </Text>
                          </Td>
                        ))}
                      </Tr>

                      {/* Tests Passed */}
                      <Tr>
                        <Td fontWeight="bold" position="sticky" left="0" bg={bgCard}>
                          Tests Passed
                        </Td>
                        {(comparison.runs || []).map((run, idx) => {
                          const tests = run.tests || { passed: 0, total: 0, failed: 0 };
                          return (
                            <Td key={idx}>
                              <HStack>
                                <Icon
                                  as={tests.failed === 0 ? MdCheckCircle : MdCancel}
                                  color={tests.failed === 0 ? "green.500" : "red.500"}
                                />
                                <Text>
                                  {tests.passed}/{tests.total}
                                </Text>
                              </HStack>
                            </Td>
                          );
                        })}
                      </Tr>

                      {/* Pass Rate */}
                      <Tr bg="purple.50">
                        <Td fontWeight="bold" position="sticky" left="0" bg="purple.100">
                          Pass Rate
                        </Td>
                        {(comparison.runs || []).map((run, idx) => {
                          const passRate = run.tests?.pass_rate || 0;
                          return (
                            <Td key={idx}>
                              <Badge colorScheme={getPassRateColor(passRate)} fontSize="md">
                                {passRate}%
                              </Badge>
                            </Td>
                          );
                        })}
                      </Tr>

                      {/* Duration */}
                      <Tr>
                        <Td fontWeight="bold" position="sticky" left="0" bg={bgCard}>
                          Duration
                        </Td>
                        {(comparison.runs || []).map((run, idx) => (
                          <Td key={idx}>{(run.duration_seconds || 0).toFixed(1)}s</Td>
                        ))}
                      </Tr>

                      {/* Created */}
                      <Tr>
                        <Td fontWeight="bold" position="sticky" left="0" bg={bgCard}>
                          Created At
                        </Td>
                        {(comparison.runs || []).map((run, idx) => (
                          <Td key={idx}>
                            <Text fontSize="xs">{formatDate(run.created_at)}</Text>
                          </Td>
                        ))}
                      </Tr>
                    </Tbody>
                  </Table>
                </Box>
              </CardBody>
            </Card>

            {/* Actions */}
            <HStack justify="center" spacing="4">
              <Button
                colorScheme="purple"
                variant="outline"
                onClick={() => {
                  setComparison(null);
                  setSelectedRuns([]);
                }}
              >
                New Comparison
              </Button>
              <Button
                colorScheme="blue"
                variant="outline"
                onClick={() => window.print()}
              >
                Print Report
              </Button>
            </HStack>
          </>
        )}
      </VStack>
    </Box>
  );
}