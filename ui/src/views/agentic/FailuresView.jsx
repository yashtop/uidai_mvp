// ui/src/views/agentic/FailuresView.jsx
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
  Button,
  Icon,
  Image,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  useDisclosure,
  Accordion,
  AccordionItem,
  AccordionButton,
  AccordionPanel,
  AccordionIcon,
  Code,
  useColorModeValue,
  Fade,
  Divider,
} from "@chakra-ui/react";
import { useParams, useNavigate } from "react-router-dom";
import { MdBugReport, MdImage, MdCode, MdZoomIn } from "react-icons/md";
import axios from "axios";

const API = process.env.REACT_APP_API_BASE || "http://localhost:8000";

export default function FailuresView() {
  const { runId } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [failuresData, setFailuresData] = useState(null);
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedImage, setSelectedImage] = useState(null);

  const bgCard = useColorModeValue("white", "gray.800");
  const textColor = useColorModeValue("gray.900", "white");
  const textColorSecondary = useColorModeValue("gray.600", "gray.400");

  useEffect(() => {
    loadFailures();
  }, [runId]);

  async function loadFailures() {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.get(`${API}/api/run/${runId}/failures`);
      if (res.data.ok) {
        setFailuresData(res.data);
      } else {
        setError(res.data.message || "No failure data available");
      }
    } catch (e) {
      console.error("Failed to load failures:", e);
      setError(e.response?.data?.detail || e.message || "Failed to load failures");
    } finally {
      setLoading(false);
    }
  }

  function openImageModal(imageUrl, testName) {
    setSelectedImage({ url: imageUrl, testName });
    onOpen();
  }

  if (loading) {
    return (
      <Box p="6" textAlign="center">
        <Spinner size="xl" color="red.500" thickness="4px" mb="4" />
        <Text color={textColorSecondary}>Loading failure details...</Text>
      </Box>
    );
  }

  if (error) {
    return (
      <Box p="6">
        <Alert status="info" rounded="md">
          <AlertIcon />
          <Box>
            <AlertTitle>No Failures Found</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Box>
        </Alert>
        <Button mt="4" onClick={() => navigate("/admin/runs")}>
          Back to Dashboard
        </Button>
      </Box>
    );
  }

  if (!failuresData || failuresData.failureCount === 0) {
    return (
      <Box p="6">
        <Alert status="success" rounded="md">
          <AlertIcon />
          <Box>
            <AlertTitle>✅ No Failures</AlertTitle>
            <AlertDescription>All tests passed successfully!</AlertDescription>
          </Box>
        </Alert>
        <Button mt="4" onClick={() => navigate("/admin/runs")}>
          Back to Dashboard
        </Button>
      </Box>
    );
  }

  const { failures = [], failureCount = 0 } = failuresData;

  return (
    <Fade in={true}>
      <Box p="6">
        <VStack align="stretch" spacing="6">
          {/* Header */}
          <HStack justify="space-between" align="start">
            <Box>
              <Heading size="lg" mb="2" color={textColor}>
                <Icon as={MdBugReport} mr="2" mb="-1px" color="red.500" />
                Test Failures with Screenshots
              </Heading>
              <Text color={textColorSecondary}>
                Failed tests and their captured screenshots
              </Text>
            </Box>
            <Button size="sm" onClick={() => navigate("/admin/runs")}>
              Back to Dashboard
            </Button>
          </HStack>

          {/* Summary */}
          <Alert status="error" rounded="xl" variant="left-accent" boxShadow="md">
            <AlertIcon />
            <Box flex="1">
              <AlertTitle fontSize="lg" fontWeight="bold">
                {failureCount} Test{failureCount !== 1 ? "s" : ""} Failed
              </AlertTitle>
              <AlertDescription fontSize="sm" mt="1">
                {failures.filter(f => f.hasScreenshot).length} with screenshots captured
              </AlertDescription>
            </Box>
          </Alert>

          {/* Failures List */}
          <Accordion allowMultiple defaultIndex={[0]}>
            {failures.map((failure, idx) => (
              <FailureItem
                key={idx}
                failure={failure}
                index={idx}
                runId={runId}
                onImageClick={openImageModal}
                bgCard={bgCard}
                textColor={textColor}
                textColorSecondary={textColorSecondary}
              />
            ))}
          </Accordion>
        </VStack>

        {/* Image Modal */}
        <Modal isOpen={isOpen} onClose={onClose} size="6xl">
          <ModalOverlay />
          <ModalContent>
            <ModalHeader>
              {selectedImage?.testName || "Screenshot"}
            </ModalHeader>
            <ModalCloseButton />
            <ModalBody pb="6">
              {selectedImage && (
                <Image
                  src={selectedImage.url}
                  alt="Test failure screenshot"
                  maxW="100%"
                  rounded="md"
                  boxShadow="lg"
                />
              )}
            </ModalBody>
          </ModalContent>
        </Modal>
      </Box>
    </Fade>
  );
}

// Individual failure item component
function FailureItem({ failure, index, runId, onImageClick, bgCard, textColor, textColorSecondary }) {
  const test = failure.test || {};
  const screenshots = failure.screenshots || [];
  const hasScreenshot = failure.hasScreenshot;

  const testName = test.nodeid || "Unknown Test";
  const errorMessage = test.call?.longrepr || test.error || "No error details available";
  const duration = test.duration || 0;

  return (
    <AccordionItem
      border="2px"
      borderColor="red.200"
      rounded="lg"
      mb="3"
      bg="red.50"
    >
      <AccordionButton py="4" _hover={{ bg: "red.100" }}>
        <Box flex="1" textAlign="left">
          <HStack spacing="3" mb="2">
            <Badge colorScheme="red" fontSize="md" px="3" py="1">
              Failure {index + 1}
            </Badge>
            {hasScreenshot && (
              <Badge colorScheme="blue" fontSize="sm">
                <Icon as={MdImage} mb="-1px" mr="1" />
                {screenshots.length} screenshot{screenshots.length !== 1 ? "s" : ""}
              </Badge>
            )}
            <Badge colorScheme="gray" fontSize="xs">
              {duration.toFixed(2)}s
            </Badge>
          </HStack>
          <Text fontSize="sm" fontFamily="monospace" color={textColor} isTruncated>
            {testName}
          </Text>
        </Box>
        <AccordionIcon />
      </AccordionButton>

      <AccordionPanel pb="4">
        <VStack align="stretch" spacing="4">
          {/* Test Info */}
          <Box>
            <Text fontSize="sm" fontWeight="semibold" color={textColor} mb="2">
              Test: {testName}
            </Text>
            <HStack spacing="3" fontSize="xs" color={textColorSecondary}>
              <Text>Duration: {duration.toFixed(2)}s</Text>
              <Text>Outcome: {test.outcome}</Text>
            </HStack>
          </Box>

          <Divider />

          {/* Error Message */}
          <Box>
            <HStack mb="2">
              <Icon as={MdCode} color="red.500" />
              <Text fontSize="sm" fontWeight="semibold" color={textColor}>
                Error Details
              </Text>
            </HStack>
            <Box
              bg="gray.900"
              color="red.300"
              p="4"
              rounded="md"
              fontSize="xs"
              fontFamily="monospace"
              whiteSpace="pre-wrap"
              maxH="200px"
              overflowY="auto"
              border="1px"
              borderColor="gray.700"
            >
              {errorMessage}
            </Box>
          </Box>

          {/* Screenshots */}
          {hasScreenshot && (
            <Box>
              <HStack mb="3">
                <Icon as={MdImage} color="blue.500" />
                <Text fontSize="sm" fontWeight="semibold" color={textColor}>
                  Screenshots ({screenshots.length})
                </Text>
              </HStack>
              <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing="4">
                {screenshots.map((screenshot, sidx) => (
                  <Card
                    key={sidx}
                    bg={bgCard}
                    cursor="pointer"
                    onClick={() => onImageClick(`${API}${screenshot.url}`, testName)}
                    _hover={{ transform: "scale(1.02)", shadow: "lg" }}
                    transition="all 0.2s"
                  >
                    <CardBody p="0">
                      <Box position="relative">
                        <Image
                          src={`${API}${screenshot.url}`}
                          alt={screenshot.name}
                          w="100%"
                          h="200px"
                          objectFit="cover"
                          rounded="md"
                        />
                        <Box
                          position="absolute"
                          top="2"
                          right="2"
                          bg="blackAlpha.700"
                          color="white"
                          p="2"
                          rounded="md"
                        >
                          <Icon as={MdZoomIn} />
                        </Box>
                      </Box>
                      <Box p="3">
                        <Text fontSize="xs" fontWeight="semibold" color={textColor} isTruncated>
                          {screenshot.name}
                        </Text>
                        <Text fontSize="xs" color={textColorSecondary} mt="1">
                          {(screenshot.size / 1024).toFixed(1)} KB
                        </Text>
                      </Box>
                    </CardBody>
                  </Card>
                ))}
              </SimpleGrid>
            </Box>
          )}

          {!hasScreenshot && (
            <Alert status="info" size="sm" rounded="md">
              <AlertIcon />
              <Text fontSize="sm">No screenshot captured for this failure</Text>
            </Alert>
          )}
        </VStack>
      </AccordionPanel>
    </AccordionItem>
  );
}