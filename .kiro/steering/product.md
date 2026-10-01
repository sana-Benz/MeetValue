# MeetValue — Product Overview

MeetValue is a serverless web app built for a student hackathon (AWS Zero to Shipped Hackathon).

## Core Purpose
Calculate the real-time cost of internal team meetings and use AI to suggest actionable ways to reduce that cost, making the hidden cost of meetings visible before or during meeting planning.

## Key Features
- Single-page app: user inputs meeting subject, duration, and attendees with seniority level
- Instant cost calculation, displayed as a striking headline number (e.g. "This meeting costs your company $410")
- AI-powered suggestions via Claude (Amazon Bedrock) analyzing meeting context to recommend: partial attendance for specific roles, shortened duration, or making certain attendees optional
- Each recommendation includes an estimated savings amount, calculated by the app (not the AI)

## Target Users
Internal teams at companies who want visibility into the hidden cost of meetings and want to make better decisions about their time.

## Hackathon Context
- Category: Workplace Efficiency
- Track: Startup
- Must remain simple to build and deploy given limited development time and AWS beginner experience
- Must stay within AWS Free Tier / low-cost boundaries (Claude Haiku 4.5, not larger models)

## Business Model (for pitch purposes)
Freemium SaaS per team, with potential upsell toward automatic calendar integration.