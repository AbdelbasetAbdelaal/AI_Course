# 🎵 Edges Music Store - Final Testing Guide

Welcome to the final testing phase of your LangGraph Multi-Agent Application! This guide will walk you through a complete testing scenario to verify that the UI, routing, database tools, and multi-agent systems are all working in harmony.

## Step 1: Initial Setup & Authentication
1. **Start the App:** Ensure your app is running (`streamlit run music_store_app.py`) and open it in your browser.
2. **API Key:** In the sidebar under **🔑 API Key Handling**, paste your Groq API Key. 
3. **Check Status:** Look at the bottom of the sidebar. You should see a green box saying `Database Online: 59 Customers loaded.`
4. **Login:** Under **🔐 Store Authentication**, type the ID `1` or the phone number `+55 (12) 3923-5555` and click **Login Securely**. 
   *Note: You should see a success message pop up, unlocking the main chat window.*

---

## Step 2: Test the Music Catalog Sub-Agent 🎸
*This tests the first specialized agent and its connection to the database tools.*
- **Prompt:** `"What albums do you have by the artist Iron Maiden?"`
- **Expected Behavior:** The Supervisor routes to the `Music Catalog` agent, which calls `get_albums_by_artist` and lists Iron Maiden's albums from the Chinook database.

## Step 3: Test the Invoice Sub-Agent 🧾
*This tests the second specialized agent.*
- **Prompt:** `"Can you show me my most recent purchase and how much the unit price was?"`
- **Expected Behavior:** The Supervisor routes to the `Invoice Info` agent, which securely uses your logged-in Customer ID to query the database and list your recent purchases.

## Step 4: Test Long-Term Memory & Preferences 🧠
*This tests the memory extraction agent that runs silently in the background.*
- **Prompt:** `"I really love Heavy Metal music and Classic Rock. Please remember that for next time!"`
- **Expected Behavior:** The Supervisor routes to the `create_memory` agent. It silently extracts your preferences and saves them.
- **Verification Prompt:** `"Based on what you know about me, what genre of music should I look into next?"`
- **Expected Behavior:** The Music agent retrieves your saved memory and suggests Heavy Metal/Classic Rock tracks from the database!

## Step 5: Test the Multi-Agent Compound Routing 🔀
*This tests the complex routing where the Supervisor has to coordinate multiple agents for a single question.*
- **Prompt:** `"Who is my customer support representative? Also, do you have any songs in the Jazz genre?"`
- **Expected Behavior:** The Supervisor realizes this hits both domains. It will first route to the Invoice agent to look up your support rep, then the Supervisor will take the intermediate answer and route it to the Music agent to look up Jazz songs. The final response will contain answers to both questions seamlessly!

---
> [!TIP]
> **Changing Sessions**
> Want to test as a different user? Change the **Session ID** in the sidebar (e.g., to `session_2`), log in with a different customer ID (like `2`), and watch how the agents securely adapt to the new user's purchase history and memory without mixing them up!
