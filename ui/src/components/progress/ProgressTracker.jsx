// ui/src/components/progress/ProgressTracker.jsx
// FIXED VERSION - handles both JSON and plain text messages

import React, { useEffect, useState, useRef } from "react";
import {
  Box,
  Progress,
  Text,
  VStack,
  HStack,
  Badge,
  Icon,
  useColorModeValue,
  Fade,
  ScaleFade,
  Spinner,
} from "@chakra-ui/react";
import {
  MdSearch,
  MdCode,
  MdPlayArrow,
  MdAutoFixHigh,
  MdCheckCircle,
  MdError,
} from "react-icons/md";

const API_WS = process.env.REACT_APP_API_WS || "ws://localhost:8000";

const PHASE_ICONS = {
  starting: MdPlayArrow,
  discovery: MdSearch,
  generation: MdCode,
  execution: MdPlayArrow,
  healing: MdAutoFixHigh,
  completed: MdCheckCircle,
  failed: MdError,
};

const PHASE_COLORS = {
  starting: "blue",
  discovery: "purple",
  generation: "cyan",
  execution: "orange",
  healing: "blue",
  completed: "green",
  failed: "red",
};

const PHASE_LABELS = {
  starting: "Starting",
  discovery: "Discovery",
  generation: "Test Generation",
  execution: "Test Execution",
  healing: "Auto-Healing",
  completed: "Completed",
  failed: "Failed",
};

export default function ProgressTracker({ runId, onComplete }) {
  const [progress, setProgress] = useState({
    phase: "starting",
    status: "running",
    details: "Initializing...",
    progress: 0,
  });
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef(null);

  const bgCard = useColorModeValue("white", "gray.800");
  const textColor = useColorModeValue("gray.900", "white");
  const textColorSecondary = useColorModeValue("gray.600", "gray.400");

  useEffect(() => {
    // Connect to WebSocket
    const wsUrl = `${API_WS}/ws/run/${runId}/progress`;
    console.log("Connecting to:", wsUrl);

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log("✅ WebSocket connected");
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const data = event.data;
        
        // ⚠️ FIX: Ignore pong messages
        if (data === "pong") {
          console.log("💓 Received pong (keepalive)");
          return;
        }
        
        // Parse JSON data
        const progressData = JSON.parse(data);
        console.log("📊 Progress update:", progressData);
        setProgress(progressData);

        // Notify parent when completed
        if (progressData.phase === "completed" || progressData.phase === "failed") {
          if (onComplete) {
            setTimeout(() => onComplete(progressData), 2000);
          }
        }
      } catch (e) {
        console.error("Error parsing progress:", e);
        console.log("Raw message:", event.data);
      }
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
      setIsConnected(false);
    };

    ws.onclose = () => {
      console.log("WebSocket closed");
      setIsConnected(false);
    };

    // Ping every 30 seconds to keep connection alive
    const pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send("ping");
        console.log("📤 Sent ping");
      }
    }, 30000);

    return () => {
      clearInterval(pingInterval);
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    };
  }, [runId, onComplete]);

  const currentPhase = progress.phase || "starting";
  const PhaseIcon = PHASE_ICONS[currentPhase] || MdPlayArrow;
  const phaseColor = PHASE_COLORS[currentPhase] || "blue";
  const phaseLabel = PHASE_LABELS[currentPhase] || currentPhase;
  const progressPercent = progress.progress || 0;

  return (
    <Fade in={true}>
      <Box
        bg={bgCard}
        p="6"
        rounded="xl"
        shadow="lg"
        border="2px"
        borderColor={`${phaseColor}.200`}
      >
        <VStack align="stretch" spacing="4">
          {/* Header */}
          <HStack justify="space-between">
            <HStack spacing="3">
              <Icon
                as={PhaseIcon}
                boxSize="8"
                color={`${phaseColor}.500`}
              />
              <VStack align="start" spacing="0">
                <Text fontSize="lg" fontWeight="bold" color={textColor}>
                  {phaseLabel}
                </Text>
                <Text fontSize="sm" color={textColorSecondary}>
                  {progress.details || "Processing..."}
                </Text>
              </VStack>
            </HStack>
            <HStack spacing="2">
              <Badge colorScheme={phaseColor} fontSize="md" px="3" py="1">
                {progressPercent}%
              </Badge>
              {isConnected ? (
                <Badge colorScheme="green" fontSize="xs">
                  ● Live
                </Badge>
              ) : (
                <Badge colorScheme="gray" fontSize="xs">
                  ○ Connecting...
                </Badge>
              )}
            </HStack>
          </HStack>

          {/* Progress Bar */}
          <Progress
            value={progressPercent}
            size="lg"
            colorScheme={phaseColor}
            rounded="full"
            hasStripe
            isAnimated={progress.status === "running"}
          />

          {/* Phase Indicators */}
          <HStack spacing="2" justify="space-between" mt="2">
            {Object.keys(PHASE_LABELS).slice(0, -2).map((phase) => {
              const isActive = currentPhase === phase;
              const isPast = progressPercent > getPhaseProgress(phase);
              const PhIcon = PHASE_ICONS[phase];

              return (
                <VStack key={phase} spacing="1" flex="1">
                  <ScaleFade in={true} initialScale={0.8}>
                    <Box
                      bg={
                        isActive
                          ? `${PHASE_COLORS[phase]}.100`
                          : isPast
                          ? `${PHASE_COLORS[phase]}.50`
                          : "gray.100"
                      }
                      p="2"
                      rounded="full"
                      border="2px"
                      borderColor={
                        isActive
                          ? `${PHASE_COLORS[phase]}.500`
                          : isPast
                          ? `${PHASE_COLORS[phase]}.300`
                          : "gray.300"
                      }
                    >
                      <Icon
                        as={PhIcon}
                        boxSize="5"
                        color={
                          isActive || isPast
                            ? `${PHASE_COLORS[phase]}.600`
                            : "gray.400"
                        }
                      />
                    </Box>
                  </ScaleFade>
                  <Text
                    fontSize="xs"
                    color={isActive ? textColor : textColorSecondary}
                    fontWeight={isActive ? "bold" : "normal"}
                    textAlign="center"
                  >
                    {PHASE_LABELS[phase]}
                  </Text>
                </VStack>
              );
            })}
          </HStack>

          {/* ETA */}
          {progress.status === "running" && (
            <HStack justify="center" mt="2">
              <Spinner size="sm" color={`${phaseColor}.500`} />
              <Text fontSize="sm" color={textColorSecondary}>
                Estimated time: {getETA(currentPhase)}
              </Text>
            </HStack>
          )}
        </VStack>
      </Box>
    </Fade>
  );
}

// Helper functions
function getPhaseProgress(phase) {
  const phaseProgress = {
    starting: 5,
    discovery: 30,
    generation: 60,
    execution: 85,
    healing: 95,
  };
  return phaseProgress[phase] || 0;
}

function getETA(phase) {
  const etas = {
    starting: "~30 seconds",
    discovery: "~1-2 minutes",
    generation: "~30 seconds",
    execution: "~1-3 minutes",
    healing: "~30-60 seconds",
  };
  return etas[phase] || "calculating...";
}