// ui/src/views/agentic/TestsView.jsx
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
  Code,
  Accordion,
  AccordionItem,
  AccordionButton,
  AccordionPanel,
  AccordionIcon,
  Button,
  useClipboard,
} from "@chakra-ui/react";
import { useParams } from "react-router-dom";
import axios from "axios";

const API = process.env.REACT_APP_API_BASE || "http://localhost:8000";

export default function TestsView() {
  const { runId } = useParams();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [testsData, setTestsData] = useState(null);

  useEffect(() => {
    loadTests();
  }, [runId]);

  async function loadTests() {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.get(`${API}/api/run/${runId}/tests`);
      if (res.data.ok) {
        setTestsData(res.data);
      } else {
        setError(res.data.message || "Tests not yet generated");
      }
    } catch (e) {
      console.error("Failed to load tests:", e);
      setError(e.response?.data?.detail || e.message || "Failed to load tests");
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <Box p="6" textAlign="center">
        <Spinner size="xl" color="blue.500" thickness="4px" mb="4" />
        <Text color="gray.600">Loading generated tests...</Text>
      </Box>
    );
  }

  if (error) {
    return (
      <Box p="6">
        <Alert status="warning" rounded="md">
          <AlertIcon />
          <Box>
            <AlertTitle>Tests Not Available</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Box>
        </Alert>
      </Box>
    );
  }

  if (!testsData) {
    return (
      <Box p="6">
        <Alert status="info" rounded="md">
          <AlertIcon />
          No test data available
        </Alert>
      </Box>
    );
  }

  const { tests = [], metadata = {}, count = 0 } = testsData;
  const totalLines = tests.reduce((sum, t) => sum + (t.lines || 0), 0);

  return (
    <Box p="6">
      <VStack align="stretch" spacing="6">
        {/* Header */}
        <Box>
          <Heading size="lg" mb="2">
            Generated Tests
          </Heading>
          <Text color="gray.600">
            AI-generated test cases ready for execution
          </Text>
        </Box>

        {/* Summary Stats */}
        <SimpleGrid columns={{ base: 1, md: 3 }} spacing="4">
          <Card>
            <CardBody>
              <Stat>
                <StatLabel>Test Files</StatLabel>
                <StatNumber color="blue.600">{count}</StatNumber>
              </Stat>
            </CardBody>
          </Card>

          <Card>
            <CardBody>
              <Stat>
                <StatLabel>Total Lines</StatLabel>
                <StatNumber color="green.600">{totalLines}</StatNumber>
              </Stat>
            </CardBody>
          </Card>

          <Card>
            <CardBody>
              <Stat>
                <StatLabel>Generation Method</StatLabel>
                <StatNumber fontSize="lg" color="purple.600">
                  {metadata.model === "stub" ? "Stub Fallback" : `AI (${metadata.model})`}
                </StatNumber>
              </Stat>
            </CardBody>
          </Card>
        </SimpleGrid>

        {/* Metadata Alert */}
        {metadata.model === "stub" && (
          <Alert status="info" rounded="md">
            <AlertIcon />
            <Box>
              <AlertTitle fontSize="sm">Stub Test Generated</AlertTitle>
              <AlertDescription fontSize="sm">
                AI models were unavailable, so a conservative stub test was created. 
                This ensures basic functionality testing even without LLM access.
              </AlertDescription>
            </Box>
          </Alert>
        )}

        {metadata.seed && (
          <Alert status="info" rounded="md" variant="left-accent">
            <AlertIcon />
            <Box>
              <Text fontSize="sm" fontWeight="semibold">Scenario Used:</Text>
              <Text fontSize="sm" mt="1">{metadata.seed}</Text>
            </Box>
          </Alert>
        )}

        {/* Test Files List */}
        <Box>
          <Heading size="md" mb="4">
            Test Files ({count})
          </Heading>

          {tests.length === 0 ? (
            <Alert status="info" rounded="md">
              <AlertIcon />
              No test files generated yet
            </Alert>
          ) : (
            <Accordion allowMultiple>
              {tests.map((test, idx) => (
                <TestFileItem key={idx} test={test} index={idx} />
              ))}
            </Accordion>
          )}
        </Box>
      </VStack>
    </Box>
  );
}

// Separate component for each test file
function TestFileItem({ test, index }) {
  const { hasCopied, onCopy } = useClipboard(test.content || "");

  return (
    <AccordionItem border="1px" borderColor="gray.200" rounded="md" mb="2">
      <AccordionButton py="4" _hover={{ bg: "gray.50" }}>
        <Box flex="1" textAlign="left">
          <HStack spacing="3">
            <Badge colorScheme="purple" fontSize="sm">
              Test {index + 1}
            </Badge>
            <Text fontWeight="semibold" fontSize="sm" fontFamily="monospace">
              {test.filename}
            </Text>
            <Badge colorScheme="green" fontSize="xs">
              {test.lines} lines
            </Badge>
          </HStack>
          {test.path && (
            <Text fontSize="xs" color="gray.500" mt="1" fontFamily="monospace" isTruncated>
              {test.path}
            </Text>
          )}
        </Box>
        <AccordionIcon />
      </AccordionButton>

      <AccordionPanel pb="4" bg="gray.50">
        <VStack align="stretch" spacing="3">
          {/* Copy Button */}
          <HStack justify="space-between">
            <Text fontSize="sm" fontWeight="semibold" color="gray.700">
              Test Code:
            </Text>
            <Button size="xs" onClick={onCopy} colorScheme={hasCopied ? "green" : "blue"}>
              {hasCopied ? "Copied!" : "Copy Code"}
            </Button>
          </HStack>

          {/* Error Message */}
          {test.error && (
            <Alert status="error" size="sm" rounded="md">
              <AlertIcon />
              <Text fontSize="sm">{test.error}</Text>
            </Alert>
          )}

          {/* Code Display */}
          {test.content && (
            <Box
              bg="gray.900"
              color="green.300"
              p="4"
              rounded="md"
              overflowX="auto"
              maxH="500px"
              overflowY="auto"
              fontSize="xs"
              fontFamily="monospace"
              whiteSpace="pre"
              border="1px"
              borderColor="gray.700"
            >
              {test.content}
            </Box>
          )}

          {/* File Info */}
          <Box bg="white" p="3" rounded="md" border="1px" borderColor="gray.200">
            <SimpleGrid columns={2} spacing="2" fontSize="xs">
              <HStack justify="space-between">
                <Text color="gray.600">Lines:</Text>
                <Text fontWeight="medium">{test.lines}</Text>
              </HStack>
              <HStack justify="space-between">
                <Text color="gray.600">Type:</Text>
                <Text fontWeight="medium">Playwright Test</Text>
              </HStack>
            </SimpleGrid>
          </Box>
        </VStack>
      </AccordionPanel>
    </AccordionItem>
  );
}