// ui/src/views/agentic/DiscoveryView.jsx
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
  Accordion,
  AccordionItem,
  AccordionButton,
  AccordionPanel,
  AccordionIcon,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Card,
  CardHeader,
  CardBody,
  Stat,
  StatLabel,
  StatNumber,
  StatGroup,
  SimpleGrid,
  Button
} from "@chakra-ui/react";
import { useParams,useNavigate } from "react-router-dom";
import axios from "axios";

const API = process.env.REACT_APP_API_BASE || "http://localhost:8000";

export default function DiscoveryView() {
  const { runId } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [discoveryData, setDiscoveryData] = useState(null);

  useEffect(() => {
    loadDiscovery();
  }, [runId]);

  async function loadDiscovery() {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.get(`${API}/api/run/${runId}/discovery`);
      if (res.data.ok) {
        setDiscoveryData(res.data);
      } else {
        setError(res.data.message || "Discovery not yet completed");
      }
    } catch (e) {
      console.error("Failed to load discovery:", e);
      setError(e.response?.data?.detail || e.message || "Failed to load discovery");
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <Box p="6" textAlign="center">
        <Spinner size="xl" color="blue.500" thickness="4px" mb="4" />
        <Text color="gray.600">Loading discovery results...</Text>
      </Box>
    );
  }

  if (error) {
    return (
      <Box p="6">
        <Alert status="warning" rounded="md">
          <AlertIcon />
          <Box>
            <AlertTitle>Discovery Not Available</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Box>
        </Alert>
      </Box>
    );
  }

  if (!discoveryData) {
    return (
      <Box p="6">
        <Alert status="info" rounded="md">
          <AlertIcon />
          No discovery data available
        </Alert>
      </Box>
    );
  }

  const { pages = [], metadata = {} } = discoveryData;
  const totalPages = pages.length;
  const totalSelectors = pages.reduce((sum, p) => sum + (p.selectors?.length || 0), 0);
  const duration = ((metadata.end - metadata.start) || 0).toFixed(2);

  return (
    <Box p="6">
      
      <VStack align="stretch" spacing="6">
        {/* Header */}
        <HStack justify="space-between" align="start">
        <Box>

           
          <Heading size="lg" mb="2">
            Discovery Results 
          </Heading>
          
          <Text color="gray.600">
            Pages discovered and elements found during crawl
          </Text>
          
         
        </Box>
        <Button size="sm" onClick={() => navigate("/admin/runs")}>
                      Back to Dashboard
                    </Button>
 </HStack>
        {/* Summary Stats */}
        <SimpleGrid columns={{ base: 1, md: 3 }} spacing="4">
          <Card>
            <CardBody>
              <Stat>
                <StatLabel>Pages Discovered</StatLabel>
                <StatNumber color="blue.600">{totalPages}</StatNumber>
              </Stat>
            </CardBody>
          </Card>

          <Card>
            <CardBody>
              <Stat>
                <StatLabel>Elements Found</StatLabel>
                <StatNumber color="green.600">{totalSelectors}</StatNumber>
              </Stat>
            </CardBody>
          </Card>

          <Card>
            <CardBody>
              <Stat>
                <StatLabel>Duration</StatLabel>
                <StatNumber color="purple.600">{duration}s</StatNumber>
              </Stat>
            </CardBody>
          </Card>
        </SimpleGrid>

        {/* Pages List */}
        <Box>
          <Heading size="md" mb="4">
            Discovered Pages
          </Heading>

          {pages.length === 0 ? (
            <Alert status="info" rounded="md">
              <AlertIcon />
              No pages discovered yet
            </Alert>
          ) : (
            <Accordion allowMultiple>
              {pages.map((page, idx) => (
                <AccordionItem key={idx} border="1px" borderColor="gray.200" rounded="md" mb="2">
                  <AccordionButton py="4" _hover={{ bg: "gray.50" }}>
                    <Box flex="1" textAlign="left">
                      <HStack spacing="3">
                        <Badge colorScheme="blue" fontSize="sm">
                          Page {idx + 1}
                        </Badge>
                        <Text fontWeight="semibold" fontSize="sm">
                          {page.title || "Untitled Page"}
                        </Text>
                        <Badge colorScheme="green" fontSize="xs">
                          {page.selectors?.length || 0} elements
                        </Badge>
                      </HStack>
                      <Text fontSize="xs" color="gray.500" mt="1" isTruncated>
                        {page.url}
                      </Text>
                    </Box>
                    <AccordionIcon />
                  </AccordionButton>

                  <AccordionPanel pb="4" bg="gray.50">
                    <VStack align="stretch" spacing="3">
                      {/* Page URL */}
                      <Box>
                        <Text fontSize="xs" fontWeight="semibold" color="gray.600" mb="1">
                          URL:
                        </Text>
                        <Text
                          fontSize="sm"
                          fontFamily="monospace"
                          bg="white"
                          p="2"
                          rounded="md"
                          wordBreak="break-all"
                        >
                          {page.url}
                        </Text>
                      </Box>

                      {/* Error Message (if any) */}
                      {page.error && (
                        <Alert status="error" size="sm" rounded="md">
                          <AlertIcon />
                          <Text fontSize="sm">{page.error}</Text>
                        </Alert>
                      )}

                      {/* Selectors Table */}
                      {page.selectors && page.selectors.length > 0 && (
                        <Box>
                          <Text fontSize="sm" fontWeight="semibold" color="gray.700" mb="2">
                            Discovered Elements ({page.selectors.length}):
                          </Text>
                          <Box overflowX="auto" bg="white" rounded="md" border="1px" borderColor="gray.200">
                            <Table variant="simple" size="sm">
                              <Thead bg="gray.100">
                                <Tr>
                                  <Th width="40%">Selector</Th>
                                  <Th>Text Content</Th>
                                </Tr>
                              </Thead>
                              <Tbody>
                                {page.selectors.map((sel, selIdx) => (
                                  <Tr key={selIdx} _hover={{ bg: "gray.50" }}>
                                    <Td>
                                      <Text
                                        fontFamily="monospace"
                                        fontSize="xs"
                                        color="blue.600"
                                        fontWeight="medium"
                                      >
                                        {sel.selector}
                                      </Text>
                                    </Td>
                                    <Td>
                                      <Text fontSize="sm" color="gray.700" isTruncated maxW="400px">
                                        {sel.text || <em style={{ color: '#999' }}>(no text)</em>}
                                      </Text>
                                    </Td>
                                  </Tr>
                                ))}
                              </Tbody>
                            </Table>
                          </Box>
                        </Box>
                      )}

                      {/* HTML Path */}
                      {page.html_path && (
                        <Box>
                          <Text fontSize="xs" fontWeight="semibold" color="gray.600" mb="1">
                            Saved HTML:
                          </Text>
                          <Text
                            fontSize="xs"
                            fontFamily="monospace"
                            color="gray.500"
                            bg="white"
                            p="2"
                            rounded="md"
                          >
                            {page.html_path}
                          </Text>
                        </Box>
                      )}
                    </VStack>
                  </AccordionPanel>
                </AccordionItem>
              ))}
            </Accordion>
          )}
        </Box>

        {/* Metadata */}
        <Box bg="gray.50" p="4" rounded="md" border="1px" borderColor="gray.200">
          <Text fontSize="sm" fontWeight="semibold" color="gray.700" mb="2">
            Discovery Metadata
          </Text>
          <SimpleGrid columns={{ base: 1, md: 2 }} spacing="2">
            <HStack justify="space-between">
              <Text fontSize="sm" color="gray.600">Run ID:</Text>
              <Text fontSize="sm" fontFamily="monospace" fontWeight="medium">
                {metadata.runId?.slice(-8) || 'N/A'}
              </Text>
            </HStack>
            <HStack justify="space-between">
              <Text fontSize="sm" color="gray.600">Pages Found:</Text>
              <Text fontSize="sm" fontWeight="medium">{totalPages}</Text>
            </HStack>
            <HStack justify="space-between">
              <Text fontSize="sm" color="gray.600">Start Time:</Text>
              <Text fontSize="sm" fontWeight="medium">
                {metadata.start ? new Date(metadata.start * 1000).toLocaleTimeString() : 'N/A'}
              </Text>
            </HStack>
            <HStack justify="space-between">
              <Text fontSize="sm" color="gray.600">End Time:</Text>
              <Text fontSize="sm" fontWeight="medium">
                {metadata.end ? new Date(metadata.end * 1000).toLocaleTimeString() : 'N/A'}
              </Text>
            </HStack>
          </SimpleGrid>
        </Box>
      </VStack>
    </Box>
  );
}