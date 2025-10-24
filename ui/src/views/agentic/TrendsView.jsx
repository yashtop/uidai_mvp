// ui/src/views/agentic/TrendsView.jsx

import React, { useState, useEffect } from "react";
import {
  Box,
  Heading,
  Text,
  VStack,
  HStack,
  Button,
  Select,
  Card,
  CardBody,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  StatArrow,
  SimpleGrid,
  Badge,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Icon,
  Spinner,
  Alert,
  AlertIcon,
  useColorModeValue,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
} from "@chakra-ui/react";
import {
  MdTrendingUp,
  MdTrendingDown,
  MdWarning,
  MdCheckCircle,
  MdSpeed,
} from "react-icons/md";
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { useNavigate } from "react-router-dom";
import axios from "axios";

const API = process.env.REACT_APP_API_BASE || "http://localhost:8000";

export default function TrendsView() {
  const navigate = useNavigate();
  const [trends, setTrends] = useState(null);
  const [flakyTests, setFlakyTests] = useState(null);
  const [stats, setStats] = useState(null);
  const [days, setDays] = useState(7);
  const [loading, setLoading] = useState(true);

  const bgCard = useColorModeValue("white", "gray.800");

  useEffect(() => {
    loadData();
  }, [days]);

  async function loadData() {
    setLoading(true);
    try {
      const [trendsRes, flakyRes, statsRes] = await Promise.all([
        axios.get(`${API}/api/runs/trends?days=${days}`),
        axios.get(`${API}/api/runs/flaky-tests?days=${days}`),
        axios.get(`${API}/api/runs/stats`),
      ]);

      setTrends(trendsRes.data);
      setFlakyTests(flakyRes.data);
      setStats(statsRes.data);
    } catch (e) {
      console.error("Failed to load trends:", e);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <Box p="6" textAlign="center">
        <Spinner size="xl" />
        <Text mt="4">Loading trends...</Text>
      </Box>
    );
  }

  if (!trends || !stats) {
    return (
      <Box p="6">
        <Alert status="warning">
          <AlertIcon />
          No data available
        </Alert>
      </Box>
    );
  }

  // Prepare chart data
  const chartData = trends.data_points.map((point) => ({
    date: new Date(point.timestamp).toLocaleDateString(),
    passRate: point.pass_rate,
    duration: point.duration_seconds,
    passed: point.tests_passed,
    failed: point.tests_failed,
  }));

  const getPassRateColor = (rate) => {
    if (rate >= 80) return "green";
    if (rate >= 50) return "orange";
    return "red";
  };

  return (
    <Box p="6" maxW="1400px" mx="auto">
      <VStack align="stretch" spacing="6">
        {/* Header */}
        <HStack justify="space-between">
          <Box>
            <Heading size="lg" mb="2">
              <Icon as={MdTrendingUp} mr="2" />
              Test Trends & Analytics
            </Heading>
            <Text color="gray.600">Track quality metrics over time</Text>
          </Box>
          <HStack>
            <Select value={days} onChange={(e) => setDays(parseInt(e.target.value))} maxW="150px">
              <option value="7">Last 7 days</option>
              <option value="14">Last 14 days</option>
              <option value="30">Last 30 days</option>
              <option value="90">Last 90 days</option>
            </Select>
            <Button onClick={() => navigate("/admin/runs")} variant="ghost">
              ← Back
            </Button>
          </HStack>
        </HStack>

        {/* Overall Stats */}
        <SimpleGrid columns={{ base: 1, md: 4 }} spacing="4">
          <Card>
            <CardBody>
              <Stat>
                <StatLabel>Total Runs</StatLabel>
                <StatNumber>{stats.total_runs}</StatNumber>
                <StatHelpText>
                  <Icon as={MdCheckCircle} color="green.500" mr="1" />
                  {stats.success_rate}% success rate
                </StatHelpText>
              </Stat>
            </CardBody>
          </Card>

          <Card>
            <CardBody>
              <Stat>
                <StatLabel>Overall Pass Rate</StatLabel>
                <StatNumber color={getPassRateColor(stats.overall_pass_rate) + ".500"}>
                  {stats.overall_pass_rate}%
                </StatNumber>
                <StatHelpText>
                  {stats.total_tests_passed}/{stats.total_tests_executed} tests
                </StatHelpText>
              </Stat>
            </CardBody>
          </Card>

          <Card>
            <CardBody>
              <Stat>
                <StatLabel>Avg Pass Rate (Period)</StatLabel>
                <StatNumber color={getPassRateColor(trends.summary.avg_pass_rate) + ".500"}>
                  {trends.summary.avg_pass_rate}%
                </StatNumber>
                <StatHelpText>
                  σ = {trends.summary.pass_rate_stdev}%
                </StatHelpText>
              </Stat>
            </CardBody>
          </Card>

          <Card>
            <CardBody>
              <Stat>
                <StatLabel>Recent Activity</StatLabel>
                <StatNumber>{stats.recent_activity.runs_last_24h}</StatNumber>
                <StatHelpText>Runs in last 24h</StatHelpText>
              </Stat>
            </CardBody>
          </Card>
        </SimpleGrid>

        {/* Tabs */}
        <Tabs colorScheme="purple">
          <TabList>
            <Tab>📈 Pass Rate Trends</Tab>
            <Tab>⏱️ Duration Trends</Tab>
            <Tab>🔴 Flaky Tests</Tab>
            <Tab>📊 Summary</Tab>
          </TabList>

          <TabPanels>
            {/* Pass Rate Trend */}
            <TabPanel>
              <Card>
                <CardBody>
                  <Heading size="md" mb="4">
                    Pass Rate Over Time
                  </Heading>
                  <ResponsiveContainer width="100%" height={400}>
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="date" />
                      <YAxis domain={[0, 100]} />
                      <Tooltip />
                      <Legend />
                      <Line
                        type="monotone"
                        dataKey="passRate"
                        stroke="#8884d8"
                        strokeWidth={2}
                        name="Pass Rate (%)"
                      />
                    </LineChart>
                  </ResponsiveContainer>

                  <SimpleGrid columns={3} spacing="4" mt="6">
                    <Stat>
                      <StatLabel>Average</StatLabel>
                      <StatNumber>{trends.summary.avg_pass_rate}%</StatNumber>
                    </Stat>
                    <Stat>
                      <StatLabel>Median</StatLabel>
                      <StatNumber>{trends.summary.median_pass_rate}%</StatNumber>
                    </Stat>
                    <Stat>
                      <StatLabel>Std Dev</StatLabel>
                      <StatNumber>{trends.summary.pass_rate_stdev}%</StatNumber>
                    </Stat>
                  </SimpleGrid>
                </CardBody>
              </Card>
            </TabPanel>

            {/* Duration Trend */}
            <TabPanel>
              <Card>
                <CardBody>
                  <Heading size="md" mb="4">
                    Execution Duration Over Time
                  </Heading>
                  <ResponsiveContainer width="100%" height={400}>
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="date" />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      <Line
                        type="monotone"
                        dataKey="duration"
                        stroke="#82ca9d"
                        strokeWidth={2}
                        name="Duration (seconds)"
                      />
                    </LineChart>
                  </ResponsiveContainer>

                  <SimpleGrid columns={2} spacing="4" mt="6">
                    <Stat>
                      <StatLabel>Average Duration</StatLabel>
                      <StatNumber>{trends.summary.avg_duration.toFixed(1)}s</StatNumber>
                    </Stat>
                    <Stat>
                      <StatLabel>Median Duration</StatLabel>
                      <StatNumber>{trends.summary.median_duration.toFixed(1)}s</StatNumber>
                    </Stat>
                  </SimpleGrid>
                </CardBody>
              </Card>
            </TabPanel>

            {/* Flaky Tests */}
            <TabPanel>
              <Card>
                <CardBody>
                  <HStack justify="space-between" mb="4">
                    <Box>
                      <Heading size="md">Flaky Tests Detected</Heading>
                      <Text fontSize="sm" color="gray.600" mt="1">
                        Tests that sometimes pass, sometimes fail
                      </Text>
                    </Box>
                    <Badge colorScheme="red" fontSize="lg" px="3" py="1">
                      {flakyTests.flaky_tests_found} flaky
                    </Badge>
                  </HStack>

                  {flakyTests.flaky_tests_found === 0 ? (
                    <Alert status="success">
                      <AlertIcon />
                      No flaky tests detected! All tests are stable. 🎉
                    </Alert>
                  ) : (
                    <Box overflowX="auto">
                      <Table variant="simple" size="sm">
                        <Thead>
                          <Tr>
                            <Th>Test Name</Th>
                            <Th isNumeric>Total Runs</Th>
                            <Th isNumeric>Passed</Th>
                            <Th isNumeric>Failed</Th>
                            <Th isNumeric>Pass Rate</Th>
                            <Th isNumeric>Flakiness Score</Th>
                          </Tr>
                        </Thead>
                        <Tbody>
                          {flakyTests.tests.map((test, idx) => (
                            <Tr key={idx} bg={idx % 2 === 0 ? "gray.50" : "white"}>
                              <Td maxW="400px">
                                <Text fontSize="xs" fontFamily="monospace" isTruncated>
                                  {test.test_name}
                                </Text>
                              </Td>
                              <Td isNumeric>{test.total_runs}</Td>
                              <Td isNumeric>
                                <Badge colorScheme="green">{test.passed}</Badge>
                              </Td>
                              <Td isNumeric>
                                <Badge colorScheme="red">{test.failed}</Badge>
                              </Td>
                              <Td isNumeric>
                                <Badge colorScheme={getPassRateColor(test.pass_rate)}>
                                  {test.pass_rate}%
                                </Badge>
                              </Td>
                              <Td isNumeric>
                                <Badge
                                  colorScheme={
                                    test.flakiness_score > 0.4
                                      ? "red"
                                      : test.flakiness_score > 0.2
                                      ? "orange"
                                      : "yellow"
                                  }
                                >
                                  {test.flakiness_score}
                                </Badge>
                              </Td>
                            </Tr>
                          ))}
                        </Tbody>
                      </Table>
                    </Box>
                  )}
                </CardBody>
              </Card>
            </TabPanel>

            {/* Summary */}
            <TabPanel>
              <SimpleGrid columns={{ base: 1, md: 2 }} spacing="4">
                <Card>
                  <CardBody>
                    <Heading size="sm" mb="4">
                      Period Summary ({days} days)
                    </Heading>
                    <VStack align="stretch" spacing="3">
                      <HStack justify="space-between">
                        <Text>Total Runs:</Text>
                        <Badge>{trends.summary.total_runs}</Badge>
                      </HStack>
                      <HStack justify="space-between">
                        <Text>Successful Runs:</Text>
                        <Badge colorScheme="green">{trends.summary.successful_runs}</Badge>
                      </HStack>
                      <HStack justify="space-between">
                        <Text>Failed Runs:</Text>
                        <Badge colorScheme="red">{trends.summary.failed_runs}</Badge>
                      </HStack>
                      <HStack justify="space-between">
                        <Text>Self-Healing Used:</Text>
                        <Badge colorScheme="blue">{trends.summary.healing_used_count}</Badge>
                      </HStack>
                    </VStack>
                  </CardBody>
                </Card>

                <Card>
                  <CardBody>
                    <Heading size="sm" mb="4">
                      Test Statistics
                    </Heading>
                    <VStack align="stretch" spacing="3">
                      <HStack justify="space-between">
                        <Text>Total Tests:</Text>
                        <Badge>{trends.summary.total_tests}</Badge>
                      </HStack>
                      <HStack justify="space-between">
                        <Text>Tests Passed:</Text>
                        <Badge colorScheme="green">{trends.summary.total_passed}</Badge>
                      </HStack>
                      <HStack justify="space-between">
                        <Text>Tests Failed:</Text>
                        <Badge colorScheme="red">{trends.summary.total_failed}</Badge>
                      </HStack>
                      <HStack justify="space-between">
                        <Text>Overall Pass Rate:</Text>
                        <Badge
                          colorScheme={getPassRateColor(trends.summary.overall_pass_rate)}
                          fontSize="lg"
                        >
                          {trends.summary.overall_pass_rate}%
                        </Badge>
                      </HStack>
                    </VStack>
                  </CardBody>
                </Card>
              </SimpleGrid>

              {/* Timeline Chart */}
              <Card mt="4">
                <CardBody>
                  <Heading size="md" mb="4">
                    Test Results Timeline
                  </Heading>
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="date" />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      <Bar dataKey="passed" fill="#48BB78" name="Passed" />
                      <Bar dataKey="failed" fill="#F56565" name="Failed" />
                    </BarChart>
                  </ResponsiveContainer>
                </CardBody>
              </Card>
            </TabPanel>
          </TabPanels>
        </Tabs>
      </VStack>
    </Box>
  );
}