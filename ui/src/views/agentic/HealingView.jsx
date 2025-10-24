// ui/src/views/agentic/HealingView.jsx
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
} from "@chakra-ui/react";
import { useParams, useNavigate } from "react-router-dom";
import { 
  MdAutoFixHigh, 
  MdCheckCircle, 
  MdWarning,
  MdRefresh,
  MdCode,
  MdBugReport,
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
  const textColor = useColorModeValue("gray.900", "white");
  const textColorSecondary = useColorModeValue("gray.600", "gray.400");

  useEffect(() => {
    loadHealing();
  }, [runId]);

  async function loadHealing() {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.get(`${API}/api/run/${runId}/healing`);
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

  return (
    <Fade in={true}>
      <Box p="6">
        <VStack align="stretch" spacing="6">
          {/* Header */}
          <HStack justify="space-between" align="start">
            <Box>
              <Heading size="lg" mb="2" color={textColor}>
                <Icon as={MdAutoFixHigh} mr="2" mb="-1px" color="blue.500" />
                Auto-Healing Report
              </Heading>
              <Text color={textColorSecondary}>
                Automatic test failure recovery attempts and results
              </Text>
            </Box>
            <Button size="sm" onClick={() => navigate("/admin/runs")}>
              Back to Dashboard
            </Button>
          </HStack>

          {/* Overall Status */}
          <Alert 
            status={healed ? "success" : "warning"} 
            rounded="xl"
            variant="left-accent"
            boxShadow="md"
          >
            <AlertIcon />
            <Box flex="1">
              <AlertTitle fontSize="lg" fontWeight="bold">
                {healed ? "✅ Tests Successfully Healed" : "⚠️ Healing Incomplete"}
              </AlertTitle>
              <AlertDescription fontSize="sm" mt="1">
                {healed 
                  ? `All tests passed after ${healing_attempts} healing attempt(s)`
                  : `Completed ${totalAttempts} healing attempt(s), but some tests still failing`}
              </AlertDescription>
            </Box>
          </Alert>

          {/* Summary Stats */}
          <SimpleGrid columns={{ base: 2, md: 4 }} spacing="4">
            <Card bg={bgCard} boxShadow="lg">
              <CardBody>
                <Stat>
                  <StatLabel fontSize="xs" color={textColorSecondary}>Healing Attempts</StatLabel>
                  <StatNumber fontSize="3xl" color="blue.600">
                    {totalAttempts}
                  </StatNumber>
                  <StatHelpText fontSize="xs">Total tries</StatHelpText>
                </Stat>
              </CardBody>
            </Card>

            <Card bg={bgCard} boxShadow="lg">
              <CardBody>
                <Stat>
                  <StatLabel fontSize="xs" color={textColorSecondary}>Success Rate</StatLabel>
                  <StatNumber 
                    fontSize="3xl" 
                    color={successRate === 100 ? "green.600" : "orange.600"}
                  >
                    {successRate}%
                  </StatNumber>
                  <StatHelpText fontSize="xs">
                    {healed ? "Fully healed" : "Partial"}
                  </StatHelpText>
                </Stat>
              </CardBody>
            </Card>

            <Card bg={bgCard} boxShadow="lg">
              <CardBody>
                <Stat>
                  <StatLabel fontSize="xs" color={textColorSecondary}>Final Status</StatLabel>
                  <StatNumber fontSize="2xl" color={healed ? "green.600" : "red.600"}>
                    {healed ? (
                      <Icon as={MdCheckCircle} boxSize="10" />
                    ) : (
                      <Icon as={MdWarning} boxSize="10" />
                    )}
                  </StatNumber>
                  <StatHelpText fontSize="xs">
                    {healed ? "All passed" : "Some failed"}
                  </StatHelpText>
                </Stat>
              </CardBody>
            </Card>

            <Card bg={bgCard} boxShadow="lg">
              <CardBody>
                <Stat>
                  <StatLabel fontSize="xs" color={textColorSecondary}>Final Tests</StatLabel>
                  <StatNumber fontSize="3xl" color="purple.600">
                    {final_result.summary?.passed || 0}/{final_result.summary?.total || 0}
                  </StatNumber>
                  <StatHelpText fontSize="xs">Passed</StatHelpText>
                </Stat>
              </CardBody>
            </Card>
          </SimpleGrid>

          {/* Healing Progress */}
          <Box>
            <HStack justify="space-between" mb="2">
              <Text fontSize="sm" fontWeight="semibold" color={textColor}>
                Healing Progress
              </Text>
              <Badge colorScheme={healed ? "green" : "orange"} fontSize="sm">
                {healed ? "Complete" : "Incomplete"}
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
          </Box>

          <Divider />

          {/* Healing Attempts Timeline - Simplified to avoid errors */}
          <Box>
            <Heading size="md" mb="4" color={textColor}>
              <Icon as={MdRefresh} mr="2" mb="-1px" />
              Healing Attempts ({totalAttempts})
            </Heading>

            <VStack align="stretch" spacing="3">
              {attempts.map((attempt, idx) => {
                const attemptNum = attempt.attempt || (idx + 1);
                const summary = attempt.summary || {};
                const passed = summary.passed || 0;
                const failed = summary.failed || 0;
                
                return (
                  <Card key={idx} bg={bgCard} boxShadow="md">
                    <CardBody>
                      <HStack justify="space-between" mb="2">
                        <Badge colorScheme="blue" fontSize="md" px="3" py="1">
                          Attempt {attemptNum}
                        </Badge>
                        <HStack spacing="2">
                          <Badge colorScheme="green">{passed} passed</Badge>
                          <Badge colorScheme="red">{failed} failed</Badge>
                        </HStack>
                      </HStack>
                      {attempt.applied_fix && (
                        <Text fontSize="sm" color={textColorSecondary} mt="2">
                          Applied fix: {attempt.applied_fix.issue || "Unknown issue"}
                        </Text>
                      )}
                    </CardBody>
                  </Card>
                );
              })}
            </VStack>
          </Box>
        </VStack>
      </Box>
    </Fade>
  );
}