# AI Prompts — Homework 5

## Problem 2: Study the Campus Customs database

**Prompt:** please set up data/campus_customs.db, it should be campus_customs_new.bd and just campus_customs.db, they should be the same and the one with new should be the copy I update. Create output/harness.md for each table and why

## Problem 3: Build the MCP Server

**Prompt:** We are building an MPC server now in mpc_server/ use FastMCP and i want it to talk to data/campus_customs_new.bd. every agent will use the tools in this server. i want to add three tools to look at the tickets in the database. How about they are payment outgoing, payment incoming and type (so like, rent, inventory sale, etc.) , use only information from the database, dont invent. in harness.md list my tools and include what table it reads, what ticket it unlocks and a single sentence on why the tool is right for the ticket, and make it specific to the ticket. add mcp_server/README.md to explain what the mcp server is for, the database file it uses and the three tools it has

can you change ticket 3 from get tickets by type to inventory change, and make it track inventory changes and if a ticket alters that
(I changed one tool after getting a better idea of which tool to use)

## Problem 4: Add the MCP server to the vibe coder and test each tool

**Prompt:** make sure my MCP server is in my project (homework 5 folder) so that you can call the tools. Save the connection in .mcp.json at project root. Test each tool (if you haven't already) and put evidence in output/mcp_smoke/json. for every tool i want it to show the prompt I asked the vibe coder, the tool name, and the tool output which also has to match values in data/campus_customs.db


## Problem 5: Build the agent team and grow the MCP tools 

**Prompt:** Cool. now were going to build the team of agents!!! use pydanticAI to build a Boss, inventory, accounting, facilities, and customer service. make sure there are prompts, models, agent loops, so that each of these agents can work together and delegate tasks based on their specialty. put agent prompts in backend/prompts/ (one file only per agent pls) and put data types in backend/models.py, agent files under backend/ and remember only use gpt-6-luna using my portkey_api_key for the agents! here are my prompts - the boss is going to be the one that reads each ticket and decides which agent should work on the ticket and makes final call, the inventory agent checks stock by SKU/size, spots issues and decides which vendor to use for a restock. the accounting agent is used for accounting purposes like overseeing cash and invoices (outgoing/incoming payments), checking margins and preparing payments or POs for human check. facilities should be responsible for things like rent, and shop space stuff. Customer service is the agnet that works directly with customers and drafts messages for them. some rules. Human approval is required for payments (accounting), vendor wont ship new product with an unpaid invoice (accounting / inventory), vendor lead times comes from vendor table (inventory agent), if payment is made, update relevant table (accounting agent), is there isn't enough cash, the pay tool should refuse (accounting), cash only goes out in this project, no revenue made (accounting), dont email customers or call real vendors, keep drafts on the board (customer service, inventory). Last few rules - before the agents do a full run to resolve the tickets, the database must be reset to the original values. and the desk.date_today is today for the shop (10/11/26). go after it! and let me know if you anything else

if needed, add tools that the agents need to the MCP server so they can work on open tickets. take shop info from mcp server over data/campus_customs_new.db and don't invent a tools later that bypasses the MCP. Also make output/audit_trail.json and wire the agents so they append to that while running. for each agent loop record enough to audit later. addend, dont wipe every run. Also list each agent and MCP tool to harness.md and which table the tool uses. include a concise safety section that include the guardrails that my business would want when using real money and real customers. update mcp_server/README.md too so its updated with this info
(added this from Panel B)

## Problem 6: Plan the three tickets

**Prompt:** Create output/desk_tickets.html a page i can double click with one tab per ticket (101-103), and write down what i expect the team to do on each open ticket (below). Add empty cash and relfection tabs for later problems (write just coming later for now). you should fill out an expected section only, leave room for actual later, once the agents run. In the expected section, put in 101 - "The boss should call the inventory agent first to make sure that we have the tee in stock. I would expect the Boss to call the inventory and accounting agents for this ticket. It should use the inventory MCP tool, and the payment incoming tool" For ticket 102 write "I would expect the Boss to call the Facilities agent first because this ticket pertains to rent due, and that facilities agent handles that. I would expect to the boss to call the accounting tool next to oversee payment. The MCP tool used would be payment outgoing" For ticket 103 say "The Boss should call the inventory agent first, as we want to make sure we have 20 size M hoodies in stock. It should also call the customer service agent to communicate to the AI club and ask what sort of discount they want and communicat the rest of the order details through there. It should also call accounting to arrange payment and speak to the human to see what discount they are willing to give. Lastly, it should call the inventory tool, not payment incoming yet since it doesn't know how much we are able to sell / at what cost."


## Problem 7: Backend routes 

**Prompt:** time to build the backend . backend/main.py use FastAPU and create routes to that I can return three tickets and if they are resolved or open, take a ticket id and run agents on that ticket, return recent agent events, what the agents did and the tools they used (so that the board can refresh), approve payment or purchase after a human clicks approve (only prepare pay), return checking balance from cash_accounts, reset database to original values when i want to do a fresh run! I will be starting the server with a terminal command (uvicorn main:app --reload --port 8000) so make sure that all works. update harness.md to list each route in one line (the URL and what it does)

## Problem 8: Agent Dashoard

**Prompt:** it works! now let's build the board frontend! put it in frontend/ with react + vite + typescript. i need the page to can the routes i just built. I want the dashboard to list all threee tickers, let me pick a ticket and start the agent team on it, show the agent (can you make the agent look like a cartoon character of their role hahahah) and what they are doing as the ticket runs, mark a ticket resolved once its finished, show a short summary of what the agnet did, allow space for a human to approve a pay/ purchase and lastly show the checking balance (like it would drop after an approved pay) don't make it neon like usual. Make it clean but also visually interesting, no bright colors. I need the front end to work with the backend at http://localhost:8000. make sure the backend can acces the vite page origin so the browser can call the routes. start the board with terminal command npm run dev. WRite output/design.md with my specifications for the dashboard look (design, how the agents read different, how resolved tickets and cash show up and why)

Make the boss look like me (inserted photo of SOM headshot) 

## Problem 9: Resolve the Tickets 

**Prompt:** hey hey, before testing the agents on the tickers. reset the campus_customs_new.db again to start clean, then run all the tickets to they are resolved. open up output/desk_tickets.html and on each ticket tab fill in the actial section, (use same bullets from expected), on the cash tab - itemize the money with starting checking balance (after reset), for each ticket note how the cash changes when that ticket resolved and why (pay, purchase, dollar amount) and the ending checking balance (must match cash_accounts in the working database (extra check to make sure its right so i dont loose ppoints) . save output.resolved_tickets.json, in there i want you to put the final status, short outcome, what each agent contributed and any human approvals for EACH ticket. next save output/resolved_board.html a page that i can double click with a screenshot of my react board for EACH resolved ticket. append real results in the audit_trail.json and finish harness.md so that it covers MCP tools, the five agents, API routes, dashbaord safety rules and tables :)))))


## Problem 10: Reflection

**Prompt:** Okay now i need to reflect hehe. open output/desk_tickets.html and were gonna fill in the reflections tab. were going to answer the following questions "How would you evaluate the performance of the agents on each ticket and why? For each ticket, how did the Actual compare to the Expected plan I wrote earlier? What would have been simpler as one agent with tools - and why? Describe three new problems Campus Customs might face that this agent team could solve with the tools I built. Describe three new problems Campus Customs might face that this agent team could not solve with the tools I built, explain the tools and agents I would need to solve them. (using the ticket and cash tab on the same page as evidence). Please make the write up but leave places where i can fill in with my own thoughts

```

```
