---
name: ai_chat_frontend_design
description: A skill for designing and implementing the frontend for the AIChat project, focusing on admin/operator UI.
triggers:
  - "User requests frontend design and implementation for AIChat project"
boundaries:
  - "Focus on frontend design only, not backend changes"
required_tools:
  - "FastAPI"
output_format: "QA_EVIDENCE.md"
---

## Objective
The objective of this skill is to design and implement the frontend for the AIChat project, specifically focusing on the admin/operator user interface. This includes creating a practical design direction, identifying main screens, information architecture, core user flows, and visual/component structure while ensuring alignment with existing backend capabilities.

## Procedure
1. Analyze existing documentation and repository to understand the current backend capabilities and design requirements.
2. Create a design specification document that outlines the frontend design direction, including visual styles, component structures, and user flows.
3. Implement the frontend using Vite, React, and TypeScript, ensuring that the design adheres to the specified guidelines and integrates seamlessly with the FastAPI backend.
4. Conduct thorough testing to ensure all components function as intended and meet the design specifications.

## Verification Contract (NON-NEGOTIABLE)
Your job is NOT done until you provide:
- [ ] A complete design specification document for the frontend.
- [ ] A fully functional frontend implementation that adheres to the design specifications and integrates with the backend.