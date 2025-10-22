// ui/src/views/agentic/ReportView.jsx
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
  CardHeader,
  CardBody,
  SimpleGrid,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  Button,
  ButtonGroup,
  Divider,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
} from "@chakra-ui/react";
import { useParams, useNavigate } from "react-router-dom";
import axios from "axios";

const API = process.env.REACT_APP_API_BASE || "http://localhost:8000";

export default function ReportView() {
  const { runId } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [reportData, setReportData] = useState(null);

  useEffect(() => {
    loadReport();
  }, [runId]);

  async function loadReport() {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.get(`${API}/api/run/${runId}/report`);
      if (res.data.runId) {
        setReportData(res.data);
      } else {
        setError(res.data.message || "Report not yet available");
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
        <Spinner size="xl" color="blue.500" thickness="4px" mb="4" />
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
      </Box>
    );
  }

  if (!reportData) {
    return (
      <Box p="6">
        <Alert status="info" rounded="md">
          <AlertIcon />
          No report data available
        </Alert>
      </Box>
    );
  }

  const {
    targetUrl,
    status,
    createdAt,
    completedAt,
    duration,
    discovery = {},
    tests = {},
    results = {},
    healing = {},
    scenario,
  } = reportData;

  const durationMin = (duration / 60).toFixed(1);
  const passRate = results.ok && results.summary
    ? ((results.summary.passed / results.summary.total) * 100).toFixed(1)
    : 0;

  return (
    <Box p="6">
      <VStack align="stretch" spacing="6">
        {/* Header with Actions */}
        <HStack justify="space-between" align="start">
          <Box>
            <Heading size="lg" mb="2">
              Test Run Report
            </Heading>
            <Text color="gray.600" fontSize="sm" mb="1">
              Run ID: <Badge fontFamily="monospace" fontSize="xs">{runId.slice(-12)}</Badge>
            </Text>
            <Text color="gray.600" fontSize="sm">
              Target: {targetUrl}
            </Text>
          </Box>
          <ButtonGroup size="sm">
            <Button colorScheme="purple" onClick={() => navigate(`/admin/discovery/${runId}`)}>
              View Discovery
            </Button>
            <Button colorScheme="blue" onClick={() => navigate(`/admin/tests/${runId}`)}>
              View Tests
            </Button>
            <Button colorScheme="green" onClick={() => navigate(`/admin/results/${runId}`)}>
              View Results
            </Button>
          </ButtonGroup>
        </HStack>

        {/* Status Banner */}
        <Alert
          status={status === "completed" ? "success" : "error"}
          rounded="md"
          variant="left-accent"
        >
          <AlertIcon />
          <Box flex="1">
            <AlertTitle>
              {status === "completed" ? "✅ Run Completed Successfully" : "❌ Run Failed"}
            </AlertTitle>
            <AlertDescription fontSize="sm">
              Duration: {durationMin} minutes | 
              Started: {new Date(createdAt * 1000).toLocaleString()}
              {completedAt && ` | Completed: ${new Date(completedAt * 1000).toLocaleString()}`}
            </AlertDescription>
          </Box>
        </Alert>

        {/* Scenario Used */}
        {scenario && (
          <Card>
            <CardHeader pb="2">
              <Heading size="sm">Scenario Used</Heading>
            </CardHeader>
            <CardBody>
              <Text fontSize="sm" color="gray.700" whiteSpace="pre-wrap">
                {scenario}
              </Text>
            </CardBody>
          </Card>
        )}

        {/* Summary Statistics */}
        <Box>
          <Heading size="md" mb="4">
            Summary
          </Heading>
          <SimpleGrid columns={{ base: 2, md: 5 }} spacing="4">
            <Card>
              <CardBody>
                <Stat>
                  <StatLabel fontSize="xs">Pages</StatLabel>
                  <StatNumber fontSize="2xl" color="blue.600">
                    {discovery.ok ? discovery.pages?.length || 0 : "N/A"}
                  </StatNumber>
                  <StatHelpText fontSize="xs">Discovered</StatHelpText>
                </Stat>
              </CardBody>
            </Card>

            <Card>
              <CardBody>
                <Stat>
                  <StatLabel fontSize="xs">Elements</StatLabel>
                  <StatNumber fontSize="2xl" color="green.600">
                    {discovery.ok
                      ? discovery.pages?.reduce((sum, p) => sum + (p.selectors?.length || 0), 0) || 0
                      : "N/A"}
                  </StatNumber>
                  <StatHelpText fontSize="xs">Found</StatHelpText>
                </Stat>
              </CardBody>
            </Card>

            <Card>
              <CardBody>
                <Stat>
                  <StatLabel fontSize="xs">Tests</StatLabel>
                  <StatNumber fontSize="2xl" color="purple.600">
                    {tests.ok ? tests.count || 0 : "N/A"}
                  </StatNumber>
                  <StatHelpText fontSize="xs">Generated</StatHelpText>
                </Stat>
              </CardBody>
            </Card>

            <Card>
              <CardBody>
                <Stat>
                  <StatLabel fontSize="xs">Pass Rate</StatLabel>
                  <StatNumber fontSize="2xl" color={passRate >= 80 ? "green.600" : passRate >= 50 ? "orange.600" : "red.600"}>
                    {passRate}%
                  </StatNumber>
                  <StatHelpText fontSize="xs">
                    {results.ok && results.summary ? `${results.summary.passed}/${results.summary.total}` : "N/A"}
                  </StatHelpText>
                </Stat>
              </CardBody>
            </Card>

            <Card>
              <CardBody>
                <Stat>
                  <StatLabel fontSize="xs">Duration</StatLabel>
                  <StatNumber fontSize="2xl" color="blue.600">
                    {durationMin}m
                  </StatNumber>
                  <StatHelpText fontSize="xs">Total Time</StatHelpText>
                </Stat>
              </CardBody>
            </Card>
          </SimpleGrid>
        </Box>

        <Divider />

        {/* Stage-by-Stage Results */}
        <Box>
          <Heading size="md" mb="4">
            Pipeline Stages
          </Heading>

          <Tabs variant="enclosed" colorScheme="blue">
            <TabList>
              <Tab>
                <HStack spacing="2">
                  <Text>Discovery</Text>
                  {discovery.ok ? (
                    <Badge colorScheme="green" fontSize="xs">✓</Badge>
                  ) : (
                    <Badge colorScheme="red" fontSize="xs">✗</Badge>
                  )}
                </HStack>
              </Tab>
              <Tab>
                <HStack spacing="2">
                  <Text>Test Generation</Text>
                  {tests.ok ? (
                    <Badge colorScheme="green" fontSize="xs">✓</Badge>
                  ) : (
                    <Badge colorScheme="red" fontSize="xs">✗</Badge>
                  )}
                </HStack>
              </Tab>
              <Tab>
                <HStack spacing="2">
                  <Text>Execution</Text>
                  {results.ok ? (
                    <Badge colorScheme="green" fontSize="xs">✓</Badge>
                  ) : (
                    <Badge colorScheme="red" fontSize="xs">✗</Badge>
                  )}
                </HStack>
              </Tab>
              <Tab>
                <HStack spacing="2">
                  <Text>Healing</Text>
                  {healing.ok ? (
                    <Badge colorScheme="green" fontSize="xs">✓</Badge>
                  ) : (
                    <Badge colorScheme="gray" fontSize="xs">N/A</Badge>
                  )}
                </HStack>
              </Tab>
            </TabList>

            <TabPanels>
              {/* Discovery Tab */}
              <TabPanel>
                <VStack align="stretch" spacing="3">
                  {discovery.ok ? (
                    <>
                      <SimpleGrid columns={3} spacing="4">
                        <Stat>
                          <StatLabel>Pages Discovered</StatLabel>
                          <StatNumber>{discovery.pages?.length || 0}</StatNumber>
                        </Stat>
                        <Stat>
                          <StatLabel>Total Elements</StatLabel>
                          <StatNumber>
                            {discovery.pages?.reduce((sum, p) => sum + (p.selectors?.length || 0), 0) || 0}
                          </StatNumber>
                        </Stat>
                        <Stat>
                          <StatLabel>Discovery Time</StatLabel>
                          <StatNumber>
                            {discovery.metadata?.end && discovery.metadata?.start
                              ? ((discovery.metadata.end - discovery.metadata.start).toFixed(2) + "s")
                              : "N/A"}
                          </StatNumber>
                        </Stat>
                      </SimpleGrid>
                      <Button
                        size="sm"
                        colorScheme="purple"
                        onClick={() => navigate(`/admin/discovery/${runId}`)}
                      >
                        View Full Discovery Results →
                      </Button>
                    </>
                  ) : (
                    <Alert status="warning">
                      <AlertIcon />
                      Discovery stage not completed or failed
                    </Alert>
                  )}
                </VStack>
              </TabPanel>

              {/* Test Generation Tab */}
              <TabPanel>
                <VStack align="stretch" spacing="3">
                  {tests.ok ? (
                    <>
                      <SimpleGrid columns={3} spacing="4">
                        <Stat>
                          <StatLabel>Test Files</StatLabel>
                          <StatNumber>{tests.count || 0}</StatNumber>
                        </Stat>
                        <Stat>
                          <StatLabel>Total Lines</StatLabel>
                          <StatNumber>
                            {tests.tests?.reduce((sum, t) => sum + (t.lines || 0), 0) || 0}
                          </StatNumber>
                        </Stat>
                        <Stat>
                          <StatLabel>Generation Method</StatLabel>
                          <StatNumber fontSize="md">
                            {tests.metadata?.model === "stub" ? "Stub" : "AI"}
                          </StatNumber>
                        </Stat>
                      </SimpleGrid>
                      {tests.metadata?.seed && (
                        <Box bg="blue.50" p="3" rounded="md">
                          <Text fontSize="xs" fontWeight="semibold" mb="1">Scenario:</Text>
                          <Text fontSize="sm">{tests.metadata.seed}</Text>
                        </Box>
                      )}
                      <Button
                        size="sm"
                        colorScheme="blue"
                        onClick={() => navigate(`/admin/tests/${runId}`)}
                      >
                        View Generated Tests →
                      </Button>
                    </>
                  ) : (
                    <Alert status="warning">
                      <AlertIcon />
                      Test generation stage not completed or failed
                    </Alert>
                  )}
                </VStack>
              </TabPanel>

              {/* Execution Tab */}
              <TabPanel>
                <VStack align="stretch" spacing="3">
                  {results.ok ? (
                    <>
                      <SimpleGrid columns={4} spacing="4">
                        <Stat>
                          <StatLabel>Total Tests</StatLabel>
                          <StatNumber>{results.summary?.total || 0}</StatNumber>
                        </Stat>
                        <Stat>
                          <StatLabel>Passed</StatLabel>
                          <StatNumber color="green.600">{results.summary?.passed || 0}</StatNumber>
                        </Stat>
                        <Stat>
                          <StatLabel>Failed</StatLabel>
                          <StatNumber color="red.600">{results.summary?.failed || 0}</StatNumber>
                        </Stat>
                        <Stat>
                          <StatLabel>Duration</StatLabel>
                          <StatNumber>{(results.summary?.duration || 0).toFixed(2)}s</StatNumber>
                        </Stat>
                      </SimpleGrid>
                      <Alert status={results.exitCode === 0 ? "success" : "error"}>
                        <AlertIcon />
                        <Box>
                          <AlertTitle>Exit Code: {results.exitCode}</AlertTitle>
                          <AlertDescription>
                            {results.exitCode === 0 ? "All tests passed successfully" : "Some tests failed"}
                          </AlertDescription>
                        </Box>
                      </Alert>
                      <Button
                        size="sm"
                        colorScheme="green"
                        onClick={() => navigate(`/admin/results/${runId}`)}
                      >
                        View Detailed Results →
                      </Button>
                    </>
                  ) : (
                    <Alert status="warning">
                      <AlertIcon />
                      Test execution not completed or failed
                    </Alert>
                  )}
                </VStack>
              </TabPanel>

              {/* Healing Tab */}
              <TabPanel>
                <VStack align="stretch" spacing="3">
                  {healing.ok ? (
                    <>
                      <Alert status="info">
                        <AlertIcon />
                        <Box>
                          <AlertTitle>Auto-Healing Suggestions Available</AlertTitle>
                          <AlertDescription>
                            {healing.suggestions?.length || 0} healing suggestions generated by {healing.fromModel}
                          </AlertDescription>
                        </Box>
                      </Alert>
                      <SimpleGrid columns={2} spacing="4">
                        <Stat>
                          <StatLabel>Suggestions</StatLabel>
                          <StatNumber>{healing.suggestions?.length || 0}</StatNumber>
                        </Stat>
                        <Stat>
                          <StatLabel>Model Used</StatLabel>
                          <StatNumber fontSize="md">{healing.fromModel || "N/A"}</StatNumber>
                        </Stat>
                      </SimpleGrid>
                    </>
                  ) : (
                    <Alert status="info">
                      <AlertIcon />
                      No healing required - all tests passed or healing not triggered
                    </Alert>
                  )}
                </VStack>
              </TabPanel>
            </TabPanels>
          </Tabs>
        </Box>

        {/* Action Buttons */}
        <Divider />
        <HStack justify="center" spacing="4">
          <Button
            colorScheme="blue"
            size="lg"
            onClick={() => navigate("/admin/runs")}
          >
            Back to Dashboard
          </Button>
          <Button
            colorScheme="green"
            size="lg"
            variant="outline"
            onClick={() => window.print()}
          >
            Print Report
          </Button>
        </HStack>
      </VStack>
    </Box>
  );
}