import React, { useEffect, useRef, useState } from "react";
import {
  Box, Heading, Table, Thead, Tbody, Tr, Th, Td, Button, Badge, Text, Spinner, ButtonGroup, Menu, MenuButton, MenuList, MenuItem
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
  const esRef = useRef(null);
  const logsBoxRef = useRef(null);

  useEffect(() => {
    let mounted = true;
    async function load() {
      setLoadingRuns(true);
      try {
        const res = await axios.get(`${API}/api/runs`);
        if (!mounted) return;
        setRuns(res.data.runs || []);
      } catch (e) {
        console.warn("Failed to fetch runs", e);
      } finally {
        setLoadingRuns(false);
      }
    }
    load();
    const iv = setInterval(load, 4000);
    return () => { mounted = false; clearInterval(iv); };
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
    es.onopen = () => console.log("SSE: connection open for", runId);
    es.onmessage = (ev) => {
      try {
        const obj = JSON.parse(ev.data);
        if (obj && obj.line) {
          setLogs(prev => {
            const next = [...prev, obj.line];
            return next.slice(-500);
          });
        } else {
          setLogs(prev => [...prev, String(ev.data)]);
        }
      } catch (e) {
        setLogs(prev => [...prev, ev.data]);
      }
      setTimeout(() => {
        const el = logsBoxRef.current;
        if (el) el.scrollTop = el.scrollHeight;
      }, 20);
    };
    es.onerror = (err) => { console.warn("SSE error", err); };
    esRef.current = es;
  }

  function streamLogs(runId) {
    setLogs([]);
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
      <Heading size="md" mb="4">Recent Runs</Heading>

      <Box mb="4" p="3" bg="white" rounded="md" shadow="sm">
        {loadingRuns ? <Spinner /> : (
          <Table variant="simple" size="sm">
            <Thead>
              <Tr>
                <Th width="140px">Run ID</Th>
                <Th>Target</Th>
                <Th width="100px">Status</Th>
                <Th width="280px">Actions</Th>
              </Tr>
            </Thead>
            <Tbody>
              {runs.map(r => (
                <Tr key={r.runId}>
                  <Td fontFamily="monospace" fontSize="xs" isTruncated title={r.runId}>
                    {r.runId.slice(-12)}
                  </Td>
                  <Td maxW="200px" isTruncated title={r.targetUrl}>
                    {r.targetUrl}
                  </Td>
                  <Td>
                    <Badge colorScheme={getStatusColor(r.status)}>
                      {r.status}
                    </Badge>
                  </Td>
                  <Td>
                    <ButtonGroup size="xs" spacing="1">
                      <Button onClick={() => streamLogs(r.runId)}>
                        Logs
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
              {runs.length === 0 && (
                <Tr>
                  <Td colSpan={4} textAlign="center" color="gray.500" py="6">
                    No runs yet. Create one from "Start Run" page.
                  </Td>
                </Tr>
              )}
            </Tbody>
          </Table>
        )}
      </Box>

      <Box>
        <Heading size="sm" mb="2">
          Live Logs {tailingRun ? `— ${tailingRun.slice(-10)}` : ""}
        </Heading>
        <Box 
          ref={logsBoxRef} 
          id="logsBox" 
          bg="gray.900" 
          color="white" 
          p="3" 
          rounded="md" 
          maxH="320px" 
          overflowY="auto" 
          fontFamily="monospace" 
          fontSize="12px"
        >
          {logs.length === 0 ? (
            <Text color="gray.400">No logs yet — click Logs on a run to stream logs</Text>
          ) : (
            logs.map((l, i) => (
              <div key={i} style={{ whiteSpace: "pre-wrap", padding: "2px 0" }}>
                {l}
              </div>
            ))
          )}
        </Box>
      </Box>
    </Box>
  );
}