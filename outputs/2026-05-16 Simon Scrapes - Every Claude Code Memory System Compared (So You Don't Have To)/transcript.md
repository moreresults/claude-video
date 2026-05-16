# Every Claude Code Memory System Compared (So You Don't Have To)

**Channel:** Simon Scrapes  
**Duration:** 23:12  
**URL:** https://www.youtube.com/watch?v=rFWxRZ5D-lM

---

### [0:00]

Right now, Claude Code's memory system is still way behind a lot of what the open-source community has already figured out. So, in a recent video, I broke down these seven levels of Claude memory systems. And whilst researching that, I ended up digging through some really advanced setups that people are building right now. Setups like the Hermes agent, MemSearch, and a bunch of others. And to my own surprise, a lot of these systems looked incredibly advanced, but the core ideas underneath them are actually very simple to replicate.

### [0:31]

So underneath all the complexity, it always comes down to just two questions. When and how does information get written to memory? And when and how does it get retrieved again? So in this video, I'm going to show you what Claude Code's memory looks like today, what the newer systems actually doing differently, and then the setup I'd actually recommend if you want Claude Code to stop forgetting things. And one thing up front, this isn't about loading more context into Claude Code.

### [1:02]

It's about keeping context lean, only retrieving the right information when it's actually needed. So, let's get into it and we can start off by talking about the three questions that every memory system has got to answer. So, firstly, it's all about storage. How does information actually get saved and at what point? So, what happens when somebody says something to Claude that's worth remembering?

### [1:33]

How does that actually get stored in the system? So you might say our landing page is school.com/scrapes and you want Claude to always remember that information. So in some way we want the agent to actually go away and save that and we want that to be consistent and reliable or a decision like we're using Stripe not PayPal. Same thing you want that to be saved into the memory and then retrieved at a later date. So we want to understand how does information get saved with all these different memory systems.

### [2:04]

Then we want to understand how information gets injected. So you're probably familiar that the CLAUDE.md file gets injected into the system prompt whenever we prompt claude. So it's injected every single time. So how do we actually take important context of recent memory and push it to the agent during our conversation so that next time you do start a session you can open Claude Code and the memory of the most recent or most important information is loaded in automatically but it's only a snippet of that information. It's not tens of thousands of tokens.

### [2:35]

We have a small curated always there set of memory that's pushed in. So that for example Claude already knows your landing page URL or already knows your Stripe decision because we made that and that's an important decision. So we've got storage and injection. But then more importantly for long-term memories, how do we actually go and find and recover past information that we've told it? Information that we told it about client X 6 months ago.

### [3:06]

That's the information that we need to be able to recall. And this could be as recent as last week or it could be, you know, several years ago or months ago. So we might ask, what did we decide about pricing last Tuesday? And it might have a step-by-step process of let's check what's been loaded in the injection phase. If not, let's go deeper.

And if not, let's go even deeper. And we need a framework to actually store and retrieve that information from the long-term memory. So how does it store? How does it inject? And how does it recall?

### [3:36]

So these are the three themes that we're going to follow through this video and talk about the different systems like Claude Code out the box Hermes and MemSearch which are two of the best systems that I've found on the market. They often take completely different approaches. So let's get into the first section which is all about storage. So when you have a conversation with Claude it's actually autodetecting certain things you say in the background and writing them silently to MD files. These are stored at a per project level in the global space.

### [4:08]

So we've got the .claude/projects/ projects and then we're storing memory folders back there. We then have a memory.md index which is updated with all the files for which it can point to. So when you have a conversation in the future with Claude, it can always reference those files. Now this is on a per project basis. But if you repeat things multiple times and you have certain things, certain preferences that are done three or more times, then it gets promoted to a global.claude/memory folder.

### [4:39]

And you can actually see this if you go directly into your Claude Code terminal and do /memory. It will say do you want to look at your user memory which is saved in the CLAUDE.md? Do you want to look at the project memory which is also MD or do you want to open the auto-memory folder. So if you open that auto-memory folder then you can actually go and see all of the files and the index of files that that's created and you can see that those actually point to each other. So these are happening automatically in the background and I wouldn't say they're very comprehensive.

### [5:09]

is kind of mostly if you're telling it this is a really important thing but otherwise it's not really going to store a huge amount of information. Now let's look at what the open-source community has figured out around this. So how do they store and capture information as you go through? So MemSearch uses a Claude Code stop hook. So it's going to fire after every turn not just the memory worthy turns.

### [5:41]

So, it's going to call Haiku, which is going to summarize each turn into bullets. And it uses Haiku because it's a cheap fast model, and it's doing it all the time. It's going to append that data to a memory/ date file with session anchors. So, you know, when you close a session and you have a specific session ID, it's going to append that or the notes from that session to a specific memory file. So, it's storing literally everything.

### [6:13]

It then periodically runs MemSearch index or you can run this manually. Each bit of information gets chunked into a hash. Now, the reason it's converting that information into a hash is because it can then embed those chunks and turn them into vectors. Those vectors are then stored in a Milvus vector database. And it's all done locally on your CPU.

### [6:43]

So, there's zero API cost. And what this actually means for you, it's not very relevant in terms of what it's being stored as. It's being stored as vectors. So, literally a sequence of numbers. But what it does is store really effectively a meaning and a bunch of metadata associated with that specific memory.

### [7:14]

This is great for the retrieval stage later because it means we can actually retrieve information by meaning instead of just by keyword search. So not only do we have the markdown files, everything is also indexed and vectorized and put into a database in the back end automatically for us. That is absolutely critical for the retrieval stage later. And what's great about this is it basically treats markdown as the source of truth. So everything is appended as markdown and then everything else is rebuildable later from those markdown files.

### [7:44]

So if you lost this database, you could actually rebuild it from all the memories that have been appended to that date. And the other good thing about it or good and bad you could say is it captures everything. So it's not just what auto-memory from Claude Code thinks is the most relevant thing. It's actually going to capture absolutely everything. Now you might wonder is that overkill?

Well, we can come to what Hermes does in a minute and decide for yourself whether that is overkill because Hermes actually takes a completely different approach and it's closer to what Claude Code is doing out the box because actually the agent is deciding what to save. The agent has access to a couple of tools inside Hermes. So add, replace or remove and what it's doing is adding those to a memory MD file and a user.md file. So, similar to what you've seen probably in Open Claude or if you've set up your own at Genico OS, you might have a memory MD and a user.md. But this isn't the same as Claude's memory.

### [8:17]

MD. This is a memory MD with a cap on the number of characters that retains the most important information. And we'll talk about how it does that. So, memory MD stores environment information, things you've done, and then user.md is all about user profile. So, anything you say about the way you work or the way that you want to operate, user.md stores.

### [8:47]

It also has mechanisms in there for deduplicating. So whenever the agent thinks it's going to add, replace, or remove something important, it will also check for duplicates and make sure that it's not writing duplicate information to our valuable memory space. Now, all of these are kind of useless unless the information gets injected at some point, which we'll talk about next. But the important thing to know is these caps on characters enforce consolidation. So where MemSearch captures absolutely everything, the point in the Hermes memory logic is that it enforces that consolidation for when it injects that context later on.

### [9:18]

But in some ways it is very similar to MemSearch because every turn it also autosaves the complete raw transcript to a database in the background and it uses a curator. So every 7 days it goes through and prunes and consolidates all of the information that we've just talked about. So the curator's job is to keep everything clean. What it does is remove the raw transcripts from that information. So whilst MemSearch stores exact raw transcripts, Hermes actually consolidates and prunes that information.

### [9:49]

So they're actually both excellent, especially when you compare it to Claude Code. And if you look in your own memory with the auto-memory, it barely saves a thing. So MemSearch and Hermes go 10x further than the basic Claude Code out the box. So which one would I actually recommend that you use in this approach? Well, MemSearch captures everything automatically with that stop hook, but it's raw and uncurated.

### [10:21]

Hermes is going to capture our curated facts, especially those that are going to be put into memory.md and user.md, which is lean and intentionally lean, but if the agent doesn't think to save something, it's kind of like with our Claude auto-memory, it's still actually grabbing the full transcript and saving it into something that we can retrieve from a database at a later point. So my answer to which one should you actually use? I actually think we should combine the logic of both here. We should use automatic capture for completeness and then curated facts for what matters most because this is really important for the injection of the context phase.

### [10:53]

So take the best of both and combine it. So we've got a long-term search from this embedded vector database that we can search by meaning but also the power of choosing specific information to store in the memory.md and user.md. So that now that we come to the injection phase, we can actually push that information into our context without having to search through a load of raw uncurated transcripts in the background. So memory injection into the context window is quite misunderstood. It's not about loading more context in like we always talk about.

### [11:24]

It's loading the right context at the right time only. So the default behavior of Claude Code is when you start a session you inject the full CLAUDE.md and that's why we want to keep the CLAUDE.md ideally under 200 lines that goes in with the system prompt and then before you use a tool or before claude uses a tool there is actually a pre-tool use hook which grabs the memory.md index looks through those list of memory files that were stored earlier and decides does it need based on your your query to actually go and research one of those memory files and inject that into the context too. If it does, it will inject that in as additional context inside the conversation.

### [11:54]

So this is a pretty decent starting point, but actually we can learn a lot from the way Hermes does this. We already saw that it captured a user.md and memory.md file with more information that's periodically updated and consolidated. We can actually inject those into the context window. But first, let's quickly cover MemSearch because it might surprise you here, but MemSearch actually has no injection layer at all. It just relies on the default behavior of Claude Code injection, the CLAUDE.md and the memory.md.

### [12:25]

MemSearch is really built for the recall which we'll come to. So, think of MemSearch as storage and search. Basically, a storage and search library that massively improves long-term recall. Whereas Hermes, I think, nails this. So, at the session start, it basically loads a frozen snapshot similar to the way that Claude uses Claude.

### [12:56]

MD, but it will not only use the Claude MD, it will additionally add in the memory MD, the user.md, and SOUL.md every single time. And that comes to around 1,300 tokens that are put into every single conversation window. Now, this is per session because it's a frozen snapshot. So, it gets cached in the memory. So, you don't spend 1,300 tokens every time you send a message.

### [13:27]

It's just at the start of a session conversation, the session ID will have that context save. So, anything that's saved to memory MD, user.md, SOUL.md during the session will be written to the disk in the background and will not be loaded into that conversation, but will be loaded into the next conversation. So, it's a really obvious choice for what logic we'd like to use for the actual injection layer. And that's let's use Claude Code's behavior plus Hermes actual frozen snapshot to load in the memory.md, usermd and SOUL.md, which as we saw in the storage stage consolidates recently biased and most important information inside these three folders or these three markdown files.

### [13:57]

Now, yes, you are loading in compared to the huge context windows, the increased performance you're going to get from recent consolidated memories, in my opinion, is worth it. Now, this is where stuff gets really interesting in recall because this is probably the biggest gap that Claude Code has out the box. Most of the time, we're not working just on a task-by-task basis with Claude Code. We have a bunch of clients, we have a bunch of projects on the go, and actually storing that information is critical, but recall is the most important thing. If you can store as much information as you want, but if you can't get it out at the right time, then it's not worth having a good storage mechanism in the first place.

### [14:28]

And Claude Code out the box has a really poor dare I say it recall system. So basically it's user asks about the past some question about the past. It's going to check the auto-memory files which we've already seen and if it's not been saved in there it's completely lost. You might have opened the memory files that you had from earlier inside your project repository. It really is quite selective about what it saved.

### [14:58]

You probably don't have a huge amount of information stored there. So actually recalling past conversations and information, it's going to have to just go and troll through previous conversations you've had and actually burn through a load of tokens trying to find relevant information. And it has no methodology for doing so right now. Now you can of course use the resume flag to actually resume a previous conversation, but you have to know which session you actually want to resume to get that context back. So for Claude Code, the storage of information is okay.

### [15:29]

The injection is basic with just the CLAUDE.md, but the recall is actually really weak and where we can benefit most from external systems. So, how does that compare to MemSearch if a user were to ask about something from the past week, the past month, the past 6 months? Well, MemSearch has a really powerful three tier retrieval system that basically only goes deeper if it needs to. It works on the same principles of progressive disclosure.

### [16:00]

So, a user asks a question about the past and we're going to use the MemSearch search query. It's basically going to convert your query into vectors. So it can go and find in the vector database where we stored the information earlier semantic matches for your query. Then because it's stored as vectors, we'll also be able to find matches for monetization, revenue, price. So it doesn't have to be exact keyword matches.

### [16:30]

Like we're actually searching in the vector database by meaning here. And it even has a method to do that by keywords. So the dense vectors allow it to search by meaning. The BM25 keywords allow it to actually keyword match and then it's basically summarized in one list of these are the closest matches to your relevant query that you asked about the past. Now it will pass that back to the agent first and if there's nothing that's totally relevant then it's able to actually go one level deeper.

### [17:02]

So at that point it could stop and actually find really relevant queries, find exactly what we're looking for from information in the past. If that answers the question great. However, if that does not answer the question, then it jumps to tier two, which is MemSearch expand. And MemSearch expand gives it more context, more metadata, a summary of information around the match that we potentially found. And again, if that is not good enough and we need the raw dialogue, then it's going to go to the next tier, level three, which actually has all of the session dialogue that we had.

### [17:32]

Because if you remember, every single message we send, it's summarized into bullets and then appended to the memory. And then that is index. So all of the raw dialogue is actually saved and we can retrieve that with level three if we need to as a last resort. Now all of these take more tokens as we go down. But if you need a reliable system for retrieving information about your client's project 6 months ago, then MemSearch is going to be the one.

### [18:03]

Now you might have identified the limitation in this approach which is if we're asking about the past, it immediately thinks okay instead of searching the local context, let's go and do a database query. So that's going to be slower than just checking our local in context memory. So Hermes uses a really clever approach for this. First, instead of going deeper into the database, it's actually just going to check our memory.md like has the question that the user has asked been actually accessible via just the memory.md, which means it can actually get it from the context that it's already received.

So the power in injecting this frozen snapshot means that actually for some queries it's going to be able to be answered just from the context that's already in the memory and that will basically be zero cost and instantaneously accessible. So it should in theory always search the context of that existing conversation before it goes down to the levels and searches the database. So if it is not found in there then it goes deeper and searches the sessions and we already mentioned those were stored in a database the same as we did for MemSearch but instead of being a vector database is just searching by keywords effectively. So then what it's going to do is basically return the top three matching se sessions by relevance and summarize it using Gemini flash and pass that back into the agent. So Hermes is really good at exact keyword matching.

### [18:36]

So, if we were to ask it about pricing, it could find things about pricing, but it might not necessarily find things about revenue because that's by meaning and not keywords. However, they do do one really smart thing which we're going to adapt and use, which is inject this memory.md into the conversation history and then also by default as a level zero, check that memory.md. So, check what's already in context before jumping down into the MemSearch hybrid search, the MemSearch expand, and the level three down here. So what we'd actually ideally do is grab this memory.md check and put that into the MemSearch flow so that we have a hybrid of both of those. So we can treat this step as almost like a level zero between MemSearch and Hermes.

### [19:06]

So that we actually check what's already in context before we go deeper and check the vector database. So user asks about the past. It's going to check the memory MD and the context that's in that existing window. And if not found, then it's going to go on to the MemSearch to start searching the vector database by keyword and meaning and then continue to level two and level three if it needs to do so. So that's a lot of information.

### [19:37]

Now, how do you actually set this up for yourself and take the best elements of each system that can be worked together? So here's what I'd actually recommend when taking the best from each system. So let's run through store, inject, and recall and the life cycle of a conversation as it happens. So, but we will of course leverage everything that's already built into Claude Code that works well as best practice. So as a conversation happens, we're going to leverage the auto-memory which is built in and saves those memory files to the claude global folder for us.

### [20:07]

But after every turn completes, we're going to add in the MemSearch stop hook. That's basically going to capture word for word all of our transcript of our conversation so that those can be put into a daily memory. But what we want to do is maintain a memory.md and a user.md file so that actually if the agent decides that something is important, it's not just relying on Claude Code to add, replace or remove into memory.md or user.md files. Now that covers actually storing more context so that we can actually retrieve it later.

### [20:37]

We of course also leverage the vector database of MemSearch which is actually consolidating this information into long-term semantically searchable memory. So basically we're going to run a nightly job to consolidate all the information that were put into that database. All the transcripts, all the raw transcripts are going to be consolidated using this MemSearch index every single night. And if all of this is sounding a little bit too complex for you to actually go and set up, then I'm going to show you later where we've got an exact guide for free on how to give this plan to Claude Code and it will go through all your file systems and work out how to actually implement this and do all the installations for you. Now injection, we actually leveraged Hermes logic.

### [21:07]

So when the session starts, we want to inject a little bit more context than just CLAUDE.md. We want to inject the SOUL.md, the user.md, memory.md, and then possibly today's log. If you could also inject yesterday's log if you think that would be relevant too. So that would be 3,000 tokens that are cached at the start of every session which will really be important when we come to actually recalling it. So then we jump onto the recall segment of the flow.

### [21:39]

And what we've done here is combine the tier zero of Hermes where we check the memory MD and daily log first. So those are injected inside the system prompt every time we send a message but they're cached. So what we're doing is basically before digging deeper into the vector database to search past history, we check the local recent data that's been loaded into the conversation already. So memory MD and daily log that has zero cost and it's also pretty much immediate because it already has it in context. If that is not found, then we jump onto the MemSearch traditional level one, level two, level three where we search the queries using the hybrid keyword and semantic or vector search.

### [22:11]

We then expand those with the chunks and then if we do not find the information still then we can actually pass the raw transcripts and pass that information back to the agents. So this setup gives us the ability to actually search information really quickly from local recent files and prioritize those but also gives us the ability to actually search further back in less recent history to recall all knowledge to the point where we can literally pull out the raw dialogue at the end. The one thing I want you to take away is none of this is complicated individually, but it's all about preserving best practice for storage, injection, and recall so that we can massively improve the memory usage inside your Claude Code sessions. If you're working on projects and multiple clients, then this is an absolute must-have. And I know Anthropic are working on their own memory systems, but right now it's far far behind what you can get from systems that are currently open source and free to access.

### [22:41]

Now, I'll link below a completely free plan. MD document for you to pass this into Claude and set it up for yourself. Now, if you do want this straight out the box done for you, you know it's going to work well, then we'll be implementing this inside our own Agentic operating system next week. That's also linked down inside the academy in the description below. Now, if you want to see what other options I considered for memory, check out the next video.

Thanks for watching.
