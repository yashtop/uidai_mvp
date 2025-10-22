import React, { useEffect, useRef, useState } from "react";
import {
  Box, Heading, Table, Thead, Tbody, Tr, Th, Td, Button, Badge, 
  Text, Spinner, ButtonGroup, Menu, MenuButton, MenuList, MenuItem,
  Alert, AlertIcon,
} from "@chakra-ui/react";
import { ChevronDownIcon } from "@chakra-ui/icons";
import { useNavigate } from "react-router-dom";
import axios from "axios";

const API = process.env.REACT_APP_API_BASE || "http://localhost:8000";

export default function RunsDashboard() {
  const navigate = useNavigate();
  const [runs, setRuns] = useState([]);
  const [logs, setLogs] = useState([]);
  const [tailingRun, setTailingRun] = useState(null);
  const [loadingRuns, setLoadingRuns] = useState(false);
  const [error, setError] = useState(null);
  const esRef = useRef(null);
  const logsBoxRef = useRef(null);

  useEffect(() => {
    let mounted = true;
    
    async function load() {
      setLoadingRuns(true);
      setError(null);
      try {
        const res = await axios.get(`${API}/api/runs`);
        if (!mounted) return;
        setRuns(res.data.runs || []);
      } catch (e) {
        console.error("Failed to fetch runs", e);
        setError(e.message);
      } finally {
        setLoadingRuns(false);
      }
    }
    
    load();
    const iv = setInterval(load, 5000); // Refresh every 5 seconds
    
    return () => { 
      mounted = false; 
      clearInterval(iv); 
    };
  }, []);

  useEffect(() => {
    return () => {
      if (esRef.current) {
        try { esRef.current.close(); } catch (e) {}
        esRef.current = null;
      }
    };
  }, []);

  function openEventSource(runId) {
    if (esRef.current) {
      try { esRef.current.close(); } catch (e) {}
      esRef.current = null;
    }
    
    const url = `${API}/api/run/${runId}/logs/stream`;
    console.log("Opening SSE:", url);

    const es = new EventSource(url);
    
    es.onopen = () => {
      console.log("✅ SSE: Connection open for", runId);
    };
    
    es.onmessage = (ev) => {
      try {
        const obj = JSON.parse(ev.data);
        if (obj && obj.line) {
          setLogs(prev => {
            const next = [...prev, obj.line];
            return next.slice(-500); // Keep last 500 lines
          });
        } else {
          setLogs(prev => [...prev, String(ev.data)]);
        }
      } catch (e) {
        setLogs(prev => [...prev, ev.data]);
      }
      
      // Auto-scroll to bottom
      setTimeout(() => {
        const el = logsBoxRef.current;
        if (el) el.scrollTop = el.scrollHeight;
      }, 20);
    };
    
    es.onerror = (err) => {
      console.warn("SSE error", err);
    };
    
    esRef.current = es;
  }

  function streamLogs(runId) {
    setLogs([`📡 Connecting to logs for ${runId.slice(-12)}...`]);
    setTailingRun(runId);
    openEventSource(runId);
  }

  function getStatusColor(status) {
    switch(status) {
      case "completed": return "green";
      case "failed": return "red";
      case "running": return "blue";
      case "queued": return "yellow";
      default: return "gray";
    }
  }

  const isCompleted = (status) => status === "completed" || status === "failed";

  return (
    <Box>
      <Heading size="lg" mb="2">Test Runs Dashboard</Heading>
      <Text color="gray.600" mb="6" fontSize="sm">
        Monitor and manage all test executions
      </Text>

      {/* Runs Table */}
      <Box mb="6" p="4" bg="white" rounded="md" shadow="sm">
        {error && (
          <Alert status="error" mb="4" rounded="md">
            <AlertIcon />
            Failed to load runs: {error}
          </Alert>
        )}
        
        {loadingRuns ? (
          <Box textAlign="center" py="8">
            <Spinner size="xl" color="blue.500" thickness="3px" />
            <Text mt="3" color="gray.600">Loading runs...</Text>
          </Box>
        ) : (
          <Table variant="simple" size="sm">
            <Thead bg="gray.50">
              <Tr>
                <Th width="140px">Run ID</Th>
                <Th>Target URL</Th>
                <Th width="100px">Status</Th>
                <Th width="140px">Created</Th>
                <Th width="280px">Actions</Th>
              </Tr>
            </Thead>
            <Tbody>
              {runs.map(r => (
                <Tr key={r.runId} _hover={{ bg: "gray.50" }}>
                  <Td fontFamily="monospace" fontSize="xs" isTruncated title={r.runId}>
                    {r.runId.slice(-12)}
                  </Td>
                  <Td maxW="250px" isTruncated title={r.targetUrl}>
                    <Text fontSize="sm">{r.targetUrl}</Text>
                  </Td>
                  <Td>
                    <Badge colorScheme={getStatusColor(r.status)} fontSize="xs">
                      {r.status}
                    </Badge>
                  </Td>
                  <Td fontSize="xs" color="gray.600">
                    {r.createdAt ? new Date(r.createdAt).toLocaleTimeString() : "N/A"}
                  </Td>
                  <Td>
                    <ButtonGroup size="xs" spacing="1">
                      <Button 
                        onClick={() => streamLogs(r.runId)}
                        colorScheme={tailingRun === r.runId ? "green" : "gray"}
                      >
                        {tailingRun === r.runId ? "📡 Live" : "Logs"}
                      </Button>
                      
                      <Menu>
                        <MenuButton
                          as={Button}
                          rightIcon={<ChevronDownIcon />}
                          isDisabled={r.status === "queued"}
                          colorScheme="purple"
                        >
                          View
                        </MenuButton>
                        <MenuList fontSize="sm">
                          <MenuItem onClick={() => navigate(`/admin/discovery/${r.runId}`)}>
                            🔍 Discovery
                          </MenuItem>
                          <MenuItem onClick={() => navigate(`/admin/tests/${r.runId}`)}>
                            📝 Tests
                          </MenuItem>
                          <MenuItem 
                            onClick={() => navigate(`/admin/results/${r.runId}`)}
                            isDisabled={!isCompleted(r.status)}
                          >
                            ✅ Results
                          </MenuItem>
                        </MenuList>
                      </Menu>

                      <Button 
                        colorScheme="blue" 
                        onClick={() => navigate(`/admin/report/${r.runId}`)}
                        isDisabled={!isCompleted(r.status)}
                      >
                        Report
                      </Button>
                    </ButtonGroup>
                  </Td>
                </Tr>
              ))}
              {runs.length === 0 && !loadingRuns && (
                <Tr>
                  <Td colSpan={5} textAlign="center" color="gray.500" py="8">
                    <Text fontSize="md" mb="2">No test runs yet</Text>
                    <Button 
                      size="sm" 
                      colorScheme="blue" 
                      onClick={() => navigate("/admin/start")}
                    >
                      Start Your First Run
                    </Button>
                  </Td>
                </Tr>
              )}
            </Tbody>
          </Table>
        )}
      </Box>

      {/* Live Logs Section */}
      <Box>
        <Heading size="md" mb="3">
          Live Logs 
          {tailingRun && (
            <Badge ml="2" colorScheme="green" fontSize="sm">
              {tailingRun.slice(-10)}
            </Badge>
          )}
        </Heading>
        <Box 
          ref={logsBoxRef} 
          bg="gray.900" 
          color="green.300" 
          p="4" 
          rounded="md" 
          maxH="400px" 
          overflowY="auto" 
          fontFamily="monospace" 
          fontSize="13px"
          border="1px"
          borderColor="gray.700"
        >
          {logs.length === 0 ? (
            <Text color="gray.500">
              No logs streaming. Click "Logs" on any run to view real-time logs.
            </Text>
          ) : (
            logs.map((l, i) => (
              <div key={i} style={{ whiteSpace: "pre-wrap", padding: "2px 0", lineHeight: "1.5" }}>
                {l}
              </div>
            ))
          )}
        </Box>
      </Box>
    </Box>
  );
}