// ui/src/views/agentic/RunProgress.jsx
import React, { useEffect, useState } from "react";
import {
  Box,
  Heading,
  Text,
  VStack,
  HStack,
  Button,
  Alert,
  AlertIcon,
  useColorModeValue,
  Fade,
  Icon,
} from "@chakra-ui/react";
import { useParams, useNavigate } from "react-router-dom";
import { MdArrowBack, MdDashboard } from "react-icons/md";
import ProgressTracker from "components/progress/ProgressTracker";

export default function RunProgress() {
  const { runId } = useParams();
  const navigate = useNavigate();
  const [completed, setCompleted] = useState(false);

  const textColor = useColorModeValue("gray.900", "white");
  const textColorSecondary = useColorModeValue("gray.600", "gray.400");

  const handleComplete = (progressData) => {
    console.log("Run completed:", progressData);
    setCompleted(true);
  };

  return (
    <Fade in={true}>
      <Box maxW="900px" mx="auto" p="6">
        <VStack align="stretch" spacing="6">
          {/* Header */}
          <HStack justify="space-between">
            <Box>
              <Heading size="lg" mb="2" color={textColor}>
                Test Run in Progress
              </Heading>
              <Text color={textColorSecondary} fontSize="sm">
                Run ID: <code>{runId.slice(-12)}</code>
              </Text>
            </Box>
            <Button
              size="sm"
              leftIcon={<Icon as={MdArrowBack} />}
              onClick={() => navigate("/admin/runs")}
              variant="ghost"
            >
              Dashboard
            </Button>
          </HStack>

          {/* Progress Tracker */}
          <ProgressTracker runId={runId} onComplete={handleComplete} />

          {/* Completion Message */}
          {completed && (
            <Fade in={completed}>
              <Alert status="success" rounded="xl" variant="left-accent" boxShadow="lg">
                <AlertIcon />
                <Box flex="1">
                  <Text fontWeight="bold" fontSize="lg">
                    ✅ Run Completed!
                  </Text>
                  <Text fontSize="sm" mt="1">
                    Redirecting to results...
                  </Text>
                </Box>
              </Alert>
            </Fade>
          )}

          {/* Action Buttons */}
          <HStack spacing="4" justify="center" mt="4">
            <Button
              size="lg"
              colorScheme="purple"
              leftIcon={<Icon as={MdDashboard} />}
              onClick={() => navigate("/admin/runs")}
            >
              Go to Dashboard
            </Button>
            {completed && (
              <Button
                size="lg"
                colorScheme="green"
                onClick={() => navigate(`/admin/report/${runId}`)}
              >
                View Full Report
              </Button>
            )}
          </HStack>

          {/* Info Box */}
          <Alert status="info" rounded="md" mt="4">
            <AlertIcon />
            <Box fontSize="sm">
              <Text fontWeight="semibold" mb="1">
                What's happening?
              </Text>
              <Text>
                Your test run is executing in the background. This page updates in real-time
                as each phase completes. You can safely navigate away and return later.
              </Text>
            </Box>
          </Alert>
        </VStack>
      </Box>
    </Fade>
  );
}
