import React from "react";

// Chakra imports
import { Flex, useColorModeValue } from "@chakra-ui/react";

// Custom components
import { HorizonLogo } from "components/icons/Icons";
import { HSeparator } from "components/separator/Separator";

export function SidebarBrand() {
  //   Chakra color mode
  let logoColor = useColorModeValue("navy.700", "white");

  return (
    <Flex align='center' direction='column'>
            <img src='https://uidai.gov.in/images/langPage/Page-1.svg' alt='Horizon Logo' width="200px" height="100px"/>

      <HSeparator mb='20px' mt="20px"/>
    </Flex>
  );
}

export default SidebarBrand;
