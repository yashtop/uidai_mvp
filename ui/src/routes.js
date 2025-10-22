import React from 'react';
import { Icon } from '@chakra-ui/react';
import {
  MdBarChart,
  MdHome,
  MdSearch,
  MdCode,
  MdCheckCircle,
  MdAssessment,
} from 'react-icons/md';

// Agentic Views
import RunCreator from "views/agentic/RunCreator";
import RunsDashboard from "views/agentic/RunsDashboard";
import DiscoveryView from "views/agentic/DiscoveryView";
import TestsView from "views/agentic/TestsView";
import ResultsView from "views/agentic/ResultsView";
import ReportView from "views/agentic/ReportView";

const routes = [
  {
    name: "Start Run",
    layout: "/admin",
    path: "/start",
    icon: <Icon as={MdHome} width="20px" height="20px" color="inherit" />,
    component: <RunCreator />,
  },
  {
    name: "Dashboard",
    layout: "/admin",
    path: "/runs",
    icon: <Icon as={MdBarChart} width="20px" height="20px" color="inherit" />,
    component: <RunsDashboard />,
  },
  // Detail views (hidden from sidebar)
  {
    name: "Discovery Results",
    layout: "/admin",
    path: "/discovery/:runId",
    icon: <Icon as={MdSearch} width="20px" height="20px" color="inherit" />,
    component: <DiscoveryView />,
    invisible: true,
  },
  {
    name: "Generated Tests",
    layout: "/admin",
    path: "/tests/:runId",
    icon: <Icon as={MdCode} width="20px" height="20px" color="inherit" />,
    component: <TestsView />,
    invisible: true,
  },
  {
    name: "Test Results",
    layout: "/admin",
    path: "/results/:runId",
    icon: <Icon as={MdCheckCircle} width="20px" height="20px" color="inherit" />,
    component: <ResultsView />,
    invisible: true,
  },
  {
    name: "Full Report",
    layout: "/admin",
    path: "/report/:runId",
    icon: <Icon as={MdAssessment} width="20px" height="20px" color="inherit" />,
    component: <ReportView />,
    invisible: true,
  },
];

export default routes;