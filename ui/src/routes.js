// ui/src/routes.js
import React from 'react';
import { Icon } from '@chakra-ui/react';
import {
  MdBarChart,
  MdHome,
  MdSearch,
  MdCode,
  MdCheckCircle,
  MdAssessment,
  MdDashboard,MdAutoFixHigh,MdCompareArrows
} from 'react-icons/md';

// Agentic Views
import RunCreator from "views/agentic/RunCreator";
import RunsDashboard from "views/agentic/RunsDashboard";
import DiscoveryView from "views/agentic/DiscoveryView";
import TestsView from "views/agentic/TestsView";
import ResultsView from "views/agentic/ResultsView";
import ReportView from "views/agentic/ReportView";
import HealingView from "views/agentic/HealingView"; // NEW
import FailuresView from "views/agentic/FailuresView"; // NEW
import RunProgress from "views/agentic/RunProgress";
import ComparisonView from "./views/agentic/ComparisonView";
import TrendsView from "./views/agentic/TrendsView";


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
    icon: <Icon as={MdDashboard} width="20px" height="20px" color="inherit" />,
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
    name: "Healing Report", // NEW
    layout: "/admin",
    path: "/healing/:runId",
    icon: <Icon as={MdAutoFixHigh} width="20px" height="20px" color="inherit" />,
    component: <HealingView />,
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
  {
    name: "Failures & Screenshots", // NEW
    layout: "/admin",
    path: "/failures/:runId",
    icon: <Icon as={MdAssessment} width="20px" height="20px" color="inherit" />,
    component: <FailuresView />,
    invisible: true,
  },{
    name: "Run Progress",
    layout: "/admin",
    path: "/progress/:runId",
    component: <RunProgress />,
    invisible: true,
  },
  {
    name: "Compare Runs",
    layout: "/admin",
    path: "/comparison",
    component: <ComparisonView />,
    invisible: false,
     icon: <Icon as={MdCompareArrows} width="20px" height="20px" color="inherit" />,
  },
  {
    name: "Trends & Analytics",
    layout: "/admin",
    path: "/trends",
    component: <TrendsView />,
    invisible: false,
     icon: <Icon as={MdAssessment} width="20px" height="20px" color="inherit" />,
  },
];

export default routes;