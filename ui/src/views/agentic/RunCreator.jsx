import React, { useState } from "react";
import {
  Box,
  Stack,
  Heading,
  Input,
  Select,
  Switch,
  Button,
  FormLabel,
  Textarea,
  useToast,
  Text,
  Divider,
  Collapse,
  Badge,
  Wrap,
  WrapItem,
} from "@chakra-ui/react";
import { ChevronDownIcon, ChevronUpIcon } from "@chakra-ui/icons";
import axios from "axios";

const API = process.env.REACT_APP_API_BASE || "http://localhost:8000";

// 5 Realistic myAadhaar Portal Scenarios
const SCENARIO_TEMPLATES = [
  {
    id: "uidai-homepage-navigation",
    name: "1. UIDAI Homepage & Main Navigation",
    description: "Test UIDAI English homepage structure and primary navigation",
    scenario: `Test UIDAI homepage and main navigation structure:

LANGUAGE SELECTION (Initial Page):
1. Navigate to https://uidai.gov.in/en/
2. Handle language selection page if present
3. Select "English" option and proceed
4. Wait for main homepage to load (allow 30 seconds)

HOMEPAGE STRUCTURE:
5. Verify page title contains "UIDAI" or "Unique Identification"
6. Check UIDAI logo is present in header
7. Verify main navigation menu exists
8. Check "My Aadhaar" menu item in navigation
9. Check "About UIDAI" menu item
10. Check "Contact & Support" menu item
11. Check "Media & Resources" menu item

MY AADHAAR SECTION:
12. Locate "My Aadhaar" dropdown or section
13. Check "Download Aadhaar" link exists
14. Check "Update Your Aadhaar" link exists
15. Check "Check Aadhaar Status" link exists
16. Check "Verify an Aadhaar Number" link exists
17. Verify all sub-menu items are clickable

FOOTER VERIFICATION:
18. Scroll to page footer
19. Check helpline number "1947" is displayed
20. Verify email address "help@uidai.gov.in" present
21. Check footer has "About Us" link
22. Check footer has "Contact Us" link
23. Verify social media links if present
24. Check "Privacy Policy" link in footer
25. Check "Terms of Use" link in footer

ACCESSIBILITY:
26. Verify skip to content link
27. Check proper heading hierarchy
28. Test keyboard navigation (Tab key)
29. Verify all images have alt text
30. Check page is mobile responsive`
  },
  {
    id: "uidai-my-aadhaar-services",
    name: "2. My Aadhaar Services Discovery",
    description: "Test My Aadhaar section and service pages",
    scenario: `Test My Aadhaar services section:

NAVIGATION TO SERVICES:
1. From homepage, navigate to "My Aadhaar" section
2. Wait for services page to load
3. Verify page heading contains "My Aadhaar" or "Aadhaar Services"

SERVICE CATEGORIES:
4. Check "Get Aadhaar" category exists
5. Check "Update Aadhaar" category exists
6. Check "Download Aadhaar" category exists
7. Check "Aadhaar Services" category exists
8. Verify each category has icon or image

DOWNLOAD AADHAAR SERVICE:
9. Locate "Download Aadhaar" service link
10. Click and navigate to download page
11. Verify page heading is clear
12. Check information text explains service
13. Verify "Download e-Aadhaar" button or link present
14. Check breadcrumb navigation exists

UPDATE AADHAAR SERVICE:
15. Navigate back or go to "Update Your Aadhaar"
16. Verify update options are listed
17. Check "Update Address" option exists
18. Check "Update Mobile Number" option
19. Check "Update Demographics" option
20. Verify each option has description

VERIFY AADHAAR SERVICE:
21. Navigate to "Verify an Aadhaar Number" page
22. Verify page loads successfully
23. Check page has form or description
24. Verify service purpose is explained

FORMS AND DOWNLOADS:
25. Check "Enrolment & Update Forms" link
26. Navigate to forms page
27. Verify list of forms is displayed
28. Check PDF download links are present
29. Verify form names and descriptions clear
30. Check "List of Supporting Documents" link exists`
  },
  {
    id: "uidai-about-contact",
    name: "3. About UIDAI & Contact Pages",
    description: "Test About UIDAI and Contact/Support pages",
    scenario: `Test About UIDAI and Contact sections:

ABOUT UIDAI PAGE:
1. Navigate to "About UIDAI" from main menu
2. Verify page heading contains "About"
3. Check page has introduction text about UIDAI
4. Verify "Vision & Mission" section exists
5. Check "Organization Structure" section
6. Verify "Aadhaar Act" information present
7. Check "Key Features of Aadhaar" listed

AADHAAR INFORMATION:
8. Locate "What is Aadhaar" section
9. Verify Aadhaar definition is clear
10. Check "Features of Aadhaar" listed
11. Verify "Benefits of Aadhaar" section
12. Check "Aadhaar Enrolment" process explained
13. Verify "Aadhaar Generation" process described

CONTACT & SUPPORT PAGE:
14. Navigate to "Contact & Support" page
15. Verify page heading is clear
16. Check toll-free number "1947" is prominently displayed
17. Verify email address "help@uidai.gov.in" shown
18. Check postal address of UIDAI headquarters
19. Verify regional office information present

SUPPORT RESOURCES:
20. Check "FAQs" link exists
21. Navigate to FAQs page
22. Verify FAQ categories are listed
23. Check FAQ questions are expandable/clickable
24. Verify answers are displayed

GRIEVANCE REDRESSAL:
25. Check "Grievance Redressal" section or link
26. Verify grievance filing process explained
27. Check if online grievance form exists
28. Verify contact details for complaints

ADDITIONAL LINKS:
29. Check "Downloads" section in navigation
30. Verify "Media & Resources" section accessible
31. Check press releases or news section
32. Verify all major sections load without errors`
  },
  {
    id: "uidai-enrolment-centers",
    name: "4. Locate Enrolment Centers",
    description: "Test enrolment center locator functionality",
    scenario: `Test Locate Enrolment Centers service:

NAVIGATION TO LOCATOR:
1. Navigate to "Locate Enrolment Center" page
2. Verify page heading mentions "Locate" or "Find Center"
3. Check page explains how to find centers

LOCATOR OPTIONS:
4. Check if state dropdown exists
5. Verify district dropdown exists
6. Check pincode search option if available
7. Verify "Search" button is present
8. Check if map integration exists

STATE SELECTION:
9. Click state dropdown
10. Verify all Indian states are listed (28 states + 8 UTs)
11. Select a state (e.g., "Delhi")
12. Wait for district dropdown to populate

DISTRICT SELECTION:
13. Click district dropdown after state selection
14. Verify districts for selected state are shown
15. Select a district
16. Click "Search" button

SEARCH RESULTS:
17. Verify results section displays
18. Check if center list or map shows
19. Verify center details include: name, address, services
20. Check if timings are displayed
21. Verify contact information for centers

CENTER DETAILS:
22. Check each center shows available services
23. Verify "Enrolment" service indicator
24. Check "Update" service indicator
25. Verify "Biometric Update" availability

ALTERNATIVE SEARCH:
26. Test pincode search if available
27. Enter valid pincode (e.g., "110001")
28. Click search
29. Verify results for pincode search
30. Check results are relevant to pincode entered

BHUVAN PORTAL LINK:
31. Check if link to "Bhuvan Aadhaar Portal" exists
32. Verify external link indicator if applicable`
  },
  {
    id: "uidai-faqs-help",
    name: "5. FAQs & Help Resources",
    description: "Test FAQ section and help resources",
    scenario: `Test FAQs and Help Resources section:

FAQ NAVIGATION:
1. Navigate to FAQs section from main menu or footer
2. Verify page heading says "FAQs" or "Frequently Asked Questions"
3. Check page has search functionality for FAQs

FAQ CATEGORIES:
4. Verify FAQ categories are displayed
5. Check "About Aadhaar" category exists
6. Check "Enrolment & Update" category
7. Verify "Aadhaar Services" category
8. Check "Security & Privacy" category
9. Verify "Technical Issues" category if present

FAQ STRUCTURE:
10. Click on a FAQ category to expand
11. Verify list of questions appears
12. Click on a specific question
13. Check answer is displayed clearly
14. Verify answer has relevant information
15. Test multiple FAQs in different categories

SEARCH FUNCTIONALITY:
16. Locate FAQ search box if present
17. Enter search term (e.g., "download")
18. Click search button
19. Verify relevant FAQs are displayed
20. Check search results are accurate

HELP RESOURCES:
21. Check "User Manuals" or "Guides" section
22. Verify download links for user guides
23. Check "Video Tutorials" section if available
24. Verify instructional videos are listed

CONTACT OPTIONS:
25. Check "Still have questions?" section
26. Verify helpline number displayed
27. Check email contact option
28. Verify chat support if available
29. Check grievance filing link

ACCESSIBILITY:
30. Verify FAQ accordion is keyboard accessible
31. Check screen reader compatibility
32. Test all expand/collapse functions work
33. Verify FAQ page loads quickly
34. Check mobile responsiveness of FAQ section`
  },
  {
    id: "uidai-downloads-resources",
    name: "6. Downloads & Resources Section",
    description: "Test downloads, forms, and resource materials",
    scenario: `Test Downloads and Resources section:

DOWNLOADS PAGE:
1. Navigate to "Downloads" section
2. Verify page heading is clear
3. Check page has categorized downloads

ENROLMENT FORMS:
4. Locate "Enrolment & Update Forms" section
5. Verify form categories are listed
6. Check "Resident Indian" form exists
7. Check "NRI" forms are listed
8. Verify "Foreign National" forms present
9. Check each form has description

FORM DOWNLOADS:
10. Click on a form download link
11. Verify PDF download begins or opens
12. Check file size is displayed
13. Verify form number is shown (e.g., "Form 1")
14. Test multiple form downloads

SUPPORTING DOCUMENTS:
15. Locate "List of Supporting Documents" link
16. Click and navigate to documents page
17. Verify document categories: POI, POA, DOB
18. Check Proof of Identity (POI) documents listed
19. Verify Proof of Address (POA) documents listed
20. Check Date of Birth (DOB) proof documents

USER MANUALS & GUIDES:
21. Check "User Manuals" section exists
22. Verify manuals for residents available
23. Check operator manuals if listed
24. Verify download links are functional

MOBILE APP RESOURCES:
25. Check "mAadhaar App" section
26. Verify app download links for Android
27. Check iOS app link if available
28. Verify QR code for app download

ADDITIONAL RESOURCES:
29. Check "Notifications" or "Circulars" section
30. Verify latest notifications are listed
31. Check press releases section
32. Verify all download links work correctly
33. Test PDF viewer compatibility
34. Check file naming conventions are clear`
  },
  {
    id: "uidai-media-resources",
    name: "7. Media & News Resources",
    description: "Test media gallery, press releases, and news section",
    scenario: `Test Media & Resources section:

MEDIA PAGE NAVIGATION:
1. Navigate to "Media & Resources" section
2. Verify page heading is appropriate
3. Check page has multiple media categories

PRESS RELEASES:
4. Locate "Press Releases" section
5. Verify latest press releases are listed
6. Check each release has date
7. Verify release titles are descriptive
8. Click on a press release
9. Check full content is displayed
10. Verify PDF download option if available

NEWS & UPDATES:
11. Check "News" or "Latest Updates" section
12. Verify news items are listed chronologically
13. Check news dates are displayed
14. Verify news titles are clickable
15. Test opening a news item

PHOTO GALLERY:
16. Locate "Photo Gallery" or "Images" section
17. Check if image thumbnails are displayed
18. Click on an image
19. Verify full-size image opens
20. Check image caption is shown
21. Test image navigation (next/previous)

VIDEO GALLERY:
22. Check "Videos" or "Video Gallery" section
23. Verify video thumbnails displayed
24. Click on a video
25. Check video player loads
26. Verify video plays correctly
27. Test video controls (play, pause, volume)

EVENTS & CAMPAIGNS:
28. Check "Events" section if present
29. Verify upcoming events listed
30. Check past events archive
31. Verify event details are comprehensive

SOCIAL MEDIA:
32. Check social media feed integration
33. Verify Twitter feed if present
34. Check Facebook page link
35. Verify YouTube channel link
36. Test social media sharing options

SEARCH & FILTER:
37. Check if media search exists
38. Test filtering by date
39. Verify filtering by category works
40. Check pagination for media items`
  }
];

export default function RunCreator() {
  const [url, setUrl] = useState("https://uidai.gov.in/en/");
  const [mode, setMode] = useState("headless");
  const [preset, setPreset] = useState("balanced");
  const [useOllama, setUseOllama] = useState(false);
  
  // Scenario fields
  const [scenario, setScenario] = useState("");
  const [selectedTemplate, setSelectedTemplate] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);
  
  const [isSubmitting, setIsSubmitting] = useState(false);
  const toast = useToast();

  // Load template scenario
  const loadTemplate = (templateId) => {
    const template = SCENARIO_TEMPLATES.find(t => t.id === templateId);
    if (template) {
      setScenario(template.scenario);
      setSelectedTemplate(templateId);
      toast({
        title: "Template loaded",
        description: template.name,
        status: "info",
        duration: 2000,
      });
    }
  };

  // Clear scenario
  const clearScenario = () => {
    setScenario("");
    setSelectedTemplate("");
  };

  async function startRun() {
    if (isSubmitting) return;
    if (!/^https?:\/\//.test(url)) {
      toast({ title: "Invalid URL", status: "error", duration: 2500 });
      return;
    }
    
    setIsSubmitting(true);
    try {
      const payload = {
        url,
        mode,
        preset,
        useOllama,
        runName: `manual-${Date.now()}`,
        maxHealAttempts: 1,
        ...(scenario.trim() && { scenario: scenario.trim() }),
      };
      
      const res = await axios.post(`${API}/api/run`, payload, { timeout: 15000 });
      const runId = res.data.runId;
      
      toast({
        title: "Run started",
        description: runId,
        status: "success",
        duration: 4000,
      });
      
    } catch (e) {
      toast({
        title: "Failed to start run",
        description: e?.response?.data?.error || e.message,
        status: "error",
        duration: 4000,
      });
    } finally {
      setTimeout(() => setIsSubmitting(false), 1000);
    }
  }

  return (
    <Box bg="white" p="6" rounded="md" shadow="sm">
      <Heading size="md" mb="4">
        Start a Test Run (Mimiicing Jira to Pipeline)
      </Heading>
      
      <Stack spacing={4}>
        {/* Target URL */}
        <Box>
          <FormLabel mb="1">
            Target URL
            <Badge ml="2" colorScheme="green" fontSize="10px">
              Default: myAadhaar
            </Badge>
          </FormLabel>
          <Input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://myaadhaar.uidai.gov.in/"
            size="md"
          />
          <Text fontSize="xs" color="gray.500" mt="1">
            Testing myAadhaar portal with real services. Change URL to test other sites.
          </Text>
        </Box>

        {/* Mode */}
        <Box>
          <FormLabel mb="1">Mode</FormLabel>
          <Select value={mode} onChange={(e) => setMode(e.target.value)}>
            <option value="headless">Headless (Faster, Background)</option>
            <option value="headed">Headed (Visual Browser)</option>
          </Select>
        </Box>

        {/* Preset */}
        <Box>
          <FormLabel mb="1">Preset</FormLabel>
          <Select value={preset} onChange={(e) => setPreset(e.target.value)}>
            <option value="quick">Quick (~5-10 pages, 2-3 min)</option>
            <option value="balanced">Balanced (~15-20 pages, 5-7 min)</option>
            <option value="deep">Deep (~30-50 pages, 10-15 min)</option>
          </Select>
        </Box>

        {/* Use Ollama */}
        <Box>
          <FormLabel mb="1">Use Ollama (Local LLM)</FormLabel>
          <Switch
            isChecked={useOllama}
            onChange={(e) => setUseOllama(e.target.checked)}
          />
          <Text fontSize="xs" color="gray.500" mt="1">
            Enable to use local Ollama. If disabled or unavailable, stub tests will be generated.
          </Text>
        </Box>

        <Divider />

        {/* Scenario Templates Section */}
        <Box>
          <FormLabel mb="2">
            Test Scenario Templates
            <Badge ml="2" colorScheme="green" fontSize="10px">
              myAadhaar Portal
            </Badge>
          </FormLabel>
          
          <Text fontSize="sm" color="gray.600" mb="3">
            Select a pre-built scenario for focused testing of myAadhaar services:
          </Text>

          <Stack spacing={2} mb={3}>
            {SCENARIO_TEMPLATES.map((template) => (
              <Button
                key={template.id}
                size="sm"
                variant={selectedTemplate === template.id ? "solid" : "outline"}
                colorScheme={selectedTemplate === template.id ? "blue" : "gray"}
                onClick={() => loadTemplate(template.id)}
                justifyContent="flex-start"
                height="auto"
                whiteSpace="normal"
                textAlign="left"
                py={3}
              >
                <Box>
                  <Text fontWeight="semibold">{template.name}</Text>
                  <Text fontSize="xs" color={selectedTemplate === template.id ? "blue.100" : "gray.500"} mt={1}>
                    {template.description}
                  </Text>
                </Box>
              </Button>
            ))}
          </Stack>

          {scenario && (
            <Button
              size="sm"
              variant="outline"
              colorScheme="red"
              onClick={clearScenario}
              w="full"
            >
              Clear Selected Scenario
            </Button>
          )}
        </Box>

        {/* Advanced Options Toggle */}
        {scenario && (
          <Box>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowAdvanced(!showAdvanced)}
              rightIcon={showAdvanced ? <ChevronUpIcon /> : <ChevronDownIcon />}
              w="full"
              justifyContent="space-between"
            >
              {showAdvanced ? "Hide Scenario Details" : "View/Edit Scenario Details"}
            </Button>
          </Box>
        )}

        {/* Collapsible Scenario Editor */}
        <Collapse in={showAdvanced} animateOpacity>
          <Stack spacing={3} pt={2}>
            <Box>
              <FormLabel mb="1">
                Scenario Details
                <Text as="span" fontSize="sm" color="gray.500" ml="2">
                  (Editable)
                </Text>
              </FormLabel>
              <Textarea
                value={scenario}
                onChange={(e) => setScenario(e.target.value)}
                placeholder="Test scenario will appear here..."
                rows={12}
                resize="vertical"
                fontFamily="monospace"
                fontSize="xs"
                bg="gray.50"
              />
              <Text fontSize="xs" color="gray.500" mt="1">
                💡 You can edit the scenario above or select a different template
              </Text>
            </Box>
          </Stack>
        </Collapse>

        <Divider />

        {/* Submit Button */}
        <Button
          colorScheme="blue"
          size="lg"
          onClick={startRun}
          isLoading={isSubmitting}
          loadingText="Starting Test Run..."
          isDisabled={isSubmitting}
        >
          {scenario ? "🎯 Start Test with Scenario" : "🔍 Start Auto-Discovery Test"}
        </Button>

        <Box bg="blue.50" p="3" rounded="md">
          <Text fontSize="sm" color="blue.800" fontWeight="medium">
            {scenario 
              ? "✅ AI will generate targeted tests based on your selected myAadhaar scenario"
              : "ℹ️ Without a scenario, AI will automatically discover and test all available pages"}
          </Text>
        </Box>
      </Stack>
    </Box>
  );
}