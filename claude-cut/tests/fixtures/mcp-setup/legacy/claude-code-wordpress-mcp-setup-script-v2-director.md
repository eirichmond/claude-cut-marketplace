 # Director: Connect Claude Code to WordPress with MCP (Then Lock It Down)

**23 talking head lines (about 952 words, roughly 6:21 spoken) and 41 voiceover lines (about 1540 words, roughly 10:16 spoken).**

Script: `claude-code-wordpress-mcp-setup-script-v2.md`. Every line is copied word for word from the script. Where a paragraph switches between face and screen partway through, it's split at a sentence boundary and nothing is reworded.

---

## 1. Talking head shot list

Record these in one sitting. They're in script order, so your energy follows the video's arc: light in the cold open, serious for the guard rails, relaxed for the confession.


### Cold open

**TH-01**

> While I was testing this, Claude Code got into my live WordPress site over SSH, which is not how I'd told it to get in. I'll show you exactly how that happened later, and how to stop it happening to you.

*Delivery:* Cold open. Flat and a bit rueful, not dramatic. Leave a half-beat pause after "over SSH", then land "how to stop it happening to you" as a promise.

**TH-02**

> Okay, so some of you are going to hate this. AI is everywhere, and we're using it in WordPress in all sorts of different ways now. Locally, you can spin up a WordPress site pretty easily with the Studio app and chat to the built-in AI. Fine. But I wanted to set up my own configuration, using Claude Code, talking to a real site.

*Delivery:* Relaxed and conversational. Say "some of you are going to hate this" with a knowing smile. The editor may cut away to Studio footage mid-line.

**TH-03**

> Now, there is official documentation for this. It lives on the WordPress GitHub account under the MCP Adapter repository, and it tells you how to connect your site over MCP. What it doesn't do is walk you through the couple of things you need in place first, or how to actually build the config file. So that's what this video is.

*Delivery:* Steady. Slow down on "So that's what this video is" and nod to camera. It's the video's promise.

**TH-04**

> For those of you who don't know, MCP stands for Model Context Protocol, and all it really is is a standard way for an AI agent to talk to a piece of software. Keep that in your back pocket, because I'll give you a better analogy in a minute.

*Delivery:* Explainer tone, a touch lighter. A small smile on "back pocket". The lower third sits over this.


### Step one: a user with the lowest possible role

**TH-05**

> A lot of the tutorials out there just generate the password on the admin account they're already logged in as, and you really don't want to hand an AI admin and let it go wild on your site doing things you didn't expect.

*Delivery:* Direct to camera, mildly exasperated. Lean on "admin" both times.


### Step two: an application password

**TH-06**

> So now we've got a username and an application password for our claude-ai user. On their own, they don't give an AI anything useful to work with. They just sit there.

*Delivery:* Dry. Pause before "They just sit there." It's a running gag that comes back in Step three.


### Step three: install the MCP Adapter

**TH-07**

> The magic is in how you put them together, and that's where the analogy comes in.

*Delivery:* A turn in the video. Lean in slightly on "the analogy".


### The hatch and the cupboard

**TH-08**

> Imagine you're a chef (bear with me, I was one once) and you need to get into the ingredients cupboard. The MCP server is the doorway into that cupboard. The hatch, if you like.

*Delivery:* Personality beat. Play the chef aside for real ("I was one once"). Warm and a bit playful. The kitchen MG builds in after this.

**TH-09**

> What you really need to understand is that the key to the hatch is not the adapter plugin, and it's not the user with the application password.

*Delivery:* Slow down. It's the key insight of the video, so give it weight and eye contact.


### Step four: the MCP config file

**TH-10**

> I'm using the CasaGees site, which is the pizza delivery service we run from home, a little side hustle that keeps me busy at weekends.

*Delivery:* Warm and a little proud. A human moment in the middle of a lot of code. The editor may cut to CasaGees or pizza b-roll.

**TH-11**

> Please don't be the numpty who pushes an application password to GitHub.

*Delivery:* Comedy beat. Straight to camera, deadpan, and hold a second after "GitHub". The red warning strip MG slides over this.


### Step five: fire it up

**TH-12**

> You could add this to your global Claude configuration so it's available everywhere, but I don't want that. I want the control to sit inside the project, and I only want this server running while I'm actually in the session. When I close the session, the connection closes with it, and that's a deliberate choice.

*Delivery:* Opinion. Measured and deliberate. Stress "deliberate choice".


### Put the guard rails up first

**TH-13**

> Now, remember what I said at the start about SSH? Before I create an ability, I need to show you that, because I found it out the hard way.

*Delivery:* Tone shift, serious for a second (script cue). Tighter framing. Slightly slower than the tutorial sections.

**TH-14**

> I'm using Claude Code, and it will be sneaky unless you give it some guard rails. In this project I've got config files for pulling and pushing the site, using a Ruby gem called Wordmove. While I was testing, I asked the agent to do something it couldn't do over MCP, because I hadn't created the abilities for it yet. So it went looking for another way in. It found my Wordmove config, used the SSH keys already set up on my machine, and got into the site over SSH. It went straight round the sandbox I thought it was in.

*Delivery:* The story. Tell it like you're still slightly annoyed about it. Pause after "another way in", then a flat, rueful delivery on the last line. The editor cuts away to the real terminal transcript and the chef-through-the-window MG over this.

**TH-15**

> So put the rules in writing. Tell the AI, in plain language, that when it's interacting with this site it must only use the MCP connection and the Abilities API, with no SSH and no other route in.

*Delivery:* Firm and practical. This is advice straight to the viewer.


### Now the abilities

**TH-16**

> Right. We're connected, we've got guard rails, and apart from what WordPress and WooCommerce already expose, we've got nothing of our own in the cupboard. So let's set some up.

*Delivery:* Upbeat reset after the serious section. Clap the hands or give a small "Right." energy lift.

**TH-17**

> The pain in the backside is that once Saturday evening's slots are done, somebody has to go in and regenerate them for next week, every single week. And if we forget, nobody can order.

*Delivery:* Genuine mild frustration, which makes it relatable. The calendar MG (Sunday blank with a "?") lands at the end of this.

**TH-18**

> So why not expose the slot system to the AI as an ability and let it generate them? I'll register an ability for reading and creating slots, and lock it down with its own capability so only our claude-ai user can call it.

*Delivery:* Rhetorical question to camera, then matter-of-fact on the plan.

**TH-19**

> Let's build it.

*Delivery:* Short and punchy, with a hard cut to the editor straight after.


### Confession time: I got AI to build the ability too

**TH-20**

> Okay, so I'm not going to lie to you. I got AI to build the ability as well. The prompt was something like "build me an ability using the WP Abilities API to read and update order slots", and it went off and built it for me. So what I'm doing here is walking you through the logic it came up with, which lives in its own separate plugin.

*Delivery:* Self-deprecating confession. Play it with a grin. The editor may put the prompt on screen as a text card over the second half.


### Inside the ability

**TH-21**

> I'm not going to go through all of this line by line, because it's a video in its own right.

*Delivery:* A light aside to camera. A nod to the future video.

**TH-22**

> Now, although I did get AI to write this, I do understand what it's done, because I know how the Abilities API works. It'll look slightly different for anyone else who writes this logic, or gives it a different prompt, but for my prompt it did a pretty good job and I'm happy to leave it as it is. I trust it. Like I said, maybe I'll come back and do a proper video on the ability itself, because it deserves one.

*Delivery:* Honest and relaxed (script cue). An important credibility beat for an audience wary of AI code. Don't rush "I trust it."


### End screen

**TH-23**

> If you want the theory behind all this (what the Abilities API actually is and why the official adapter matters), that's in the video on screen now. And if you've already connected an AI to your site, go and check what role it's running as. Happy building.

*Delivery:* Sign-off, framed left for the end screen. Point towards the video tile on "on screen now". Hold 2s after "Happy building".


---

## 2. Voiceover shot list

Record these in a second sitting, ideally with the screen recordings open so you can pace against them. Leave a clean second of silence before and after each take.


### Step one: a user with the lowest possible role

**VO-01**

> The first thing to do happens on your live production site, not your local one, because we're going to connect local to production and interrogate the real thing. So on your live site, create a new user. I've called mine claude-ai, and I've given it a password I'm probably never going to log in with (which doesn't matter for this connection anyway).

*On screen:* Production wp-admin: Users > Add New, typing "claude-ai" into the username field. Chapter card "1. The user" plays first.

**VO-02**

> The important bit is the role. Set it to the lowest possible, which is Subscriber.

*On screen:* Zoom on the role dropdown as Subscriber is selected. Callout: "Lowest role that does the job".


### Step two: an application password

**VO-03**

> Next, on that same user, scroll down to Application Passwords and generate one. If you've not come across these, an application password is a separate credential that lets a piece of software talk to your site without using your actual login. Give it a name, hit the button, and WordPress generates it for you and shows it once, so copy it somewhere safe because you won't see it again.

*On screen:* claude-ai profile, scrolling to Application Passwords, naming it, clicking generate. The password appears (blurred in post). Chapter card "2. The application password" plays first.


### Step three: install the MCP Adapter

**VO-04**

> Now install the official WordPress MCP Adapter plugin. As far as I know it's being assessed for the WordPress plugin directory, but at the moment it doesn't live there. It lives on GitHub under the official WordPress account, in a repo called `mcp-adapter`, and the link is in the description.

*On screen:* GitHub: WordPress/mcp-adapter repo home. Chapter card "3. The MCP Adapter" plays first.

**VO-05**

> The easiest way in is the Releases page on that repo, where there's a ready-made `mcp-adapter.zip` to download. Upload that through Plugins, Add New, on your live site, and activate it. (If you'd rather build it yourself, you can clone the repo and build the zip, but for a live site I'd stick with the tagged release.)

*On screen:* GitHub Releases page, zoom on mcp-adapter.zip, then Plugins > Add New > Upload > Activate. The bracketed aside plays over a 2s flash of a terminal git clone.

**VO-06**

> Again, on its own, it just sits there. A user with an application password does nothing, and having the adapter installed does nothing.

*On screen:* MG: three icons (user, key, plugin) appear one at a time, each greyed out.


### The hatch and the cupboard

**VO-07**

> Inside the cupboard, all the ingredients are in jars, and those jars are the Abilities API. An ability is a single thing your site can do, described in a way an AI agent can understand, like creating a post, looking up an order or regenerating delivery slots. Nothing is in the cupboard unless somebody has registered it as an ability, and every ability carries a permission check, much like the capabilities your user roles already have.

*On screen:* MG: kitchen illustration. Cupboard opens, jars appear, three jars labelled as each example is said, then padlocks appear on some jars.

**VO-08**

> So some jars have a padlock on them and some are open, depending on who's asking. Our subscriber user can't reach much, whereas an admin could reach a lot more. That's the whole point of picking the lowest role.

*On screen:* MG: a "Subscriber" figure at the hatch who can only reach the unlocked jars.

**VO-09**

> The key is the MCP configuration on your local machine. That config is what opens the hatch, and the abilities are what's on the shelves once you're in.

*On screen:* MG: a key labelled ".mcp.json" appears on the chef's side, turns, and the hatch opens.


### Step four: the MCP config file

**VO-10**

> The official docs give you a basic config, but they don't tell you where it lives or how to build it, so let's do that. In your local project folder, create a file called `.mcp.json`, which is just a JSON object.

*On screen:* Editor: project file tree, new file .mcp.json being created. Chapter card "4. The config file" plays first.

**VO-11**

> From the MCP adapter GitHub docs, you can just copy this object directly into your .mcp.json file.

*On screen:* Split screen: the GitHub CLI usage guide config example next to the editor.

**VO-12**

> At the top level we need an `mcpServers` object. You can set up multiple servers in here, but this is the bare minimum. Inside that, create an object named after the connection. I've called mine `claude-ai` to match the user.

*On screen:* Editor: typing mcpServers and then claude-ai, with each key highlighted as it's said.

**VO-13**

> Now the guts of it. `command` is `npx`, and `args` is an array with `-y` and then `@automattic/mcp-wordpress-remote@latest`.

*On screen:* Editor: typing command and args, with each key highlighted.

**VO-14**

> That's the little bridge that runs on your machine and talks to the adapter on your site.

*On screen:* MG: flow of laptop > "mcp-wordpress-remote" > internet > site with adapter.

**VO-15**

> Then the environment variables. `WP_API_URL` is your site, followed by the route to the hatch, which is `/wp-json/mcp/mcp-adapter-default-server`. That's the address the agent goes looking for.

*On screen:* Editor: typing WP_API_URL, with a callout pinned under it: /wp-json/mcp/mcp-adapter-default-server.

**VO-16**

> `WP_API_USERNAME` is the user you created, and `WP_API_PASSWORD` is the application password WordPress generated for it.

*On screen:* Editor: typing WP_API_USERNAME and WP_API_PASSWORD.

**VO-17**

> Now, for security reasons, I haven't pasted the real values in here. I've set them as environment variables on my machine and I'm referencing them with a dollar sign and the variable name in curly brackets. That way the actual password never ends up in a file that could accidentally get committed.

*On screen:* Editor: the finished .mcp.json, zoomed on the ${WP_API_USERNAME} and ${WP_API_PASSWORD} values.

**VO-18**

> Finally, and just for sanity, there's `LOG_FILE`. Point it at a subfolder of your project. Mine goes to `mcp/logs/mcp-production.log`, and when something goes wrong (and it will), that's where you look.

*On screen:* Editor: typing LOG_FILE, then the full finished file held for 5s or more with no overlays.


### Step five: fire it up

**VO-19**

> With that in place, start a Claude Code session in the project. The first thing it'll do is ask whether you want to use this MCP server, so say yes.

*On screen:* Terminal: claude launched in the project folder, zoom on the MCP server approval prompt. Chapter card "5. Connect" plays first.

**VO-20**

> Now let's try it. I'm just going to ask the agent, "can you see my site over MCP?"

*On screen:* Terminal: typing the prompt "can you see my site over MCP?" at real speed.

**VO-21**

> And there you go. It comes back with information about the site, so I can confirm it's all connected and running. Sweet huh!

*On screen:* Terminal: the response streaming in, with a zoom on the site name. Give "Sweet huh!" some genuine lift even though it's audio only.

**VO-22**

> So, to recap what you actually need: a live site somewhere, a user on it with the minimum role, an application password for that user, and the official MCP Adapter plugin installed. Then in your local project folder, a `.mcp.json` with the `mcpServers` object and an entry for your connection. That's it.

*On screen:* MG: recap checklist building one tick per item, synced to each noun.


### Quick test: what can it actually see?

**VO-23**

> Before we build anything, I want to see what a slightly more privileged role gives me. CasaGees runs on WooCommerce, so I'm going to bump the claude-ai user up from Subscriber to Shop Manager and see what comes back.

*On screen:* wp-admin: the claude-ai user's role changed from Subscriber to Shop Manager. Small lower third: "Test only".

**VO-24**

> So now I can ask things like how many orders were processed this week, or what orders are coming up, and that kind of works. Granted, it's only reading, but it shows the padlocks coming off the jars as the role changes, which is exactly what you'd expect.

*On screen:* Terminal: order questions and Claude's answers, with tool-call lines visible and customer data blurred. It then cuts to the kitchen MG, where two padlocks drop off the jars.

**VO-25**

> And I'm putting it straight back to Subscriber afterwards, because I only needed it for the test.

*On screen:* wp-admin: role set back to Subscriber, with the "User updated" notice.


### Put the guard rails up first

**VO-26**

> That goes in your project's `CLAUDE.md`, or your global one.

*On screen:* Editor: CLAUDE.md with the rule highlighted.

**VO-27**

> Then back it up with actual permissions in the hidden `.claude` folder, in `settings.local.json`, where you can deny things like SSH commands outright. Instructions are a request, whereas permissions are a wall, so use both. Belt and braces.

*On screen:* Editor: .claude/settings.local.json with the SSH deny rules highlighted, then MG: two layers, "CLAUDE.md = asks nicely" and "settings deny = actually stops it". "Belt and braces" lands on the MG.


### Now the abilities

**VO-28**

> On the CasaGees site we run a slot system. We open Thursday, Friday and Saturday, from 5pm til 9pm, and we can only do twelve pizzas in any half-hour slot. When somebody orders, that slot's capacity drops so we never over-commit, and if there are no slots left, nobody can order. That's the guard rail for customers.

*On screen:* CasaGees admin: slot management screen, with the capacity column highlighted on "twelve pizzas".

**VO-29**

> Then from Claude Cowork I can set up a skill and a schedule. I do my shifts at the weekend, and come Sunday morning the slots are already sitting there ready for customers, without me having to think about it.

*On screen:* MG: the calendar refilling itself on Sunday morning.


### Confession time: I got AI to build the ability too

**VO-30**

> Let's start with the main plugin file. Up top we've got the usual bits defined, the version and the plugin directory. Then we register an abilities category. Think of that as the shelf in the cupboard. Every ability I add to this site from now on goes on that shelf, so as the list grows it stays organised.

*On screen:* Editor: main plugin file, the constants block, then the wp_register_ability_category call. A kitchen shelf MG insert is optional.

**VO-31**

> Below that is where the order slots ability gets registered, hooked into the Abilities API. The ability itself isn't in this file though. It lives in a separate folder called abilities, and we'll have a look at that in a second.

*On screen:* Editor: scrolling to the ability registration hook.

**VO-32**

> The last thing in here is a function called `casagees_abilities_can_manage`. That's the permission callback. It checks whether the current user has a capability called `manage_casagees_slots`, which I've made up for this plugin and given to the claude-ai user and nobody else. I added it from the terminal with WP-CLI (`wp user add-cap claude-ai manage_casagees_slots`), so it sits on that one user rather than a whole role. Subscribers, customers and even Shop Managers don't have it, so they can't run the ability. That's the padlock on the jar, and only one user has the key.

*On screen:* Editor: zoom on casagees_abilities_can_manage and its current_user_can( 'manage_casagees_slots' ) check, then a terminal shot of the `wp user add-cap` command (blur the host in the prompt). Then a 2s MG insert: one padlock clicks onto the "slots" jar.


### Inside the ability

**VO-33**

> Now for the ability itself. First thing you'll see is an array called the slot schema, which is what we'll hand to the Abilities API when we register.

*On screen:* Editor: abilities folder, order slots file, the slot schema array at the top.

**VO-34**

> Registering an ability works like this. You give it a namespaced name, something like `casagees/get-order-slots`, and then an array of arguments. Most of them are self-explanatory. A label, a description, the category we set up a minute ago. Then the two that matter.

*On screen:* Editor: zoom on wp_register_ability( 'casagees/get-order-slots', with each argument soft-boxed as it's named.

**VO-35**

> The execute callback is all of the logic the ability can actually do. In this case it's interrogating the database, working out what slots exist, and taking in any parameters the AI has passed along so it's got something to reason with.

*On screen:* Editor: execute_callback highlighted, then a fast scroll through its body.

**VO-36**

> The permission callback is the function we just looked at on the other file, `casagees_abilities_can_manage`. Same padlock, wired in here.

*On screen:* Editor: the permission_callback line highlighted.

**VO-37**

> Put simply, we've registered two abilities. One to get the order slots, and one to create them. One goes and fetches the data, the other one writes it.

*On screen:* MG: two jars, "get-order-slots (read)" and "create-order-slots (write)".

**VO-38**

> Let me give you a quick overview of the get ability, because there are two parts we've not covered yet.

*On screen:* Editor: input_schema in the get ability.

**VO-39**

> The input schema is what the ability expects to be asked. It's the shape of my question, if you like. Things like dates, whether I'm asking about availability, any limits on how much to return. If I ask the AI something that doesn't fit the schema, it knows it can't use this jar.

*On screen:* Editor: highlighting the date, availability and limit properties one at a time.

**VO-40**

> The output schema is the shape of the answer. The AI takes my input, runs the ability, and gets structured data back that it already knows how to read. That's really what the Abilities API is about. Not just "here's a function", but "here's what it wants, here's what it gives back, and here's who's allowed to call it". Sweet huh!

*On screen:* Editor: output_schema highlighted, then MG: "Input schema / Output schema / Permission callback" card. Make this "Sweet huh!" different from the one in Step five.

**VO-41**

> One more important bit. In the ability's meta there's an `mcp` array with `public` set to true. Abilities are private by default, so without that the ability is registered but the MCP Adapter won't expose it, and your AI will never see the jar on the shelf. Easy one to miss.

*On screen:* Editor: the meta array, with `'mcp' => array( 'public' => true )` soft-boxed.


---

## 3. Running order

| # | Clip | Section | Words |
|---|---|---|---|
| 1 | TH-01 | Cold open | 41 |
| 2 | TH-02 | Cold open | 64 |
| 3 | TH-03 | Cold open | 61 |
| 4 | TH-04 | Cold open | 49 |
| 5 | VO-01 | Step one: a user with the lowest possible role | 62 |
| 6 | VO-02 | Step one: a user with the lowest possible role | 15 |
| 7 | TH-05 | Step one: a user with the lowest possible role | 43 |
| 8 | VO-03 | Step two: an application password | 69 |
| 9 | TH-06 | Step two: an application password | 31 |
| 10 | VO-04 | Step three: install the MCP Adapter | 50 |
| 11 | VO-05 | Step three: install the MCP Adapter | 57 |
| 12 | VO-06 | Step three: install the MCP Adapter | 23 |
| 13 | TH-07 | Step three: install the MCP Adapter | 16 |
| 14 | TH-08 | The hatch and the cupboard | 34 |
| 15 | VO-07 | The hatch and the cupboard | 76 |
| 16 | VO-08 | The hatch and the cupboard | 39 |
| 17 | TH-09 | The hatch and the cupboard | 27 |
| 18 | VO-09 | The hatch and the cupboard | 28 |
| 19 | VO-10 | Step four: the MCP config file | 41 |
| 20 | VO-11 | Step four: the MCP config file | 17 |
| 21 | VO-12 | Step four: the MCP config file | 40 |
| 22 | VO-13 | Step four: the MCP config file | 18 |
| 23 | VO-14 | Step four: the MCP config file | 17 |
| 24 | VO-15 | Step four: the MCP config file | 26 |
| 25 | TH-10 | Step four: the MCP config file | 25 |
| 26 | VO-16 | Step four: the MCP config file | 16 |
| 27 | VO-17 | Step four: the MCP config file | 52 |
| 28 | TH-11 | Step four: the MCP config file | 12 |
| 29 | VO-18 | Step four: the MCP config file | 31 |
| 30 | VO-19 | Step five: fire it up | 30 |
| 31 | TH-12 | Step five: fire it up | 55 |
| 32 | VO-20 | Step five: fire it up | 18 |
| 33 | VO-21 | Step five: fire it up | 23 |
| 34 | VO-22 | Step five: fire it up | 52 |
| 35 | VO-23 | Quick test: what can it actually see? | 39 |
| 36 | VO-24 | Quick test: what can it actually see? | 48 |
| 37 | VO-25 | Quick test: what can it actually see? | 17 |
| 38 | TH-13 | Put the guard rails up first | 29 |
| 39 | TH-14 | Put the guard rails up first | 101 |
| 40 | TH-15 | Put the guard rails up first | 38 |
| 41 | VO-26 | Put the guard rails up first | 10 |
| 42 | VO-27 | Put the guard rails up first | 38 |
| 43 | TH-16 | Now the abilities | 30 |
| 44 | VO-28 | Now the abilities | 57 |
| 45 | TH-17 | Now the abilities | 34 |
| 46 | TH-18 | Now the abilities | 43 |
| 47 | VO-29 | Now the abilities | 40 |
| 48 | TH-19 | Now the abilities | 3 |
| 49 | TH-20 | Confession time: I got AI to build the ability too | 69 |
| 50 | VO-30 | Confession time: I got AI to build the ability too | 58 |
| 51 | VO-31 | Confession time: I got AI to build the ability too | 41 |
| 52 | VO-32 | Confession time: I got AI to build the ability too | 94 |
| 53 | VO-33 | Inside the ability | 28 |
| 54 | VO-34 | Inside the ability | 43 |
| 55 | VO-35 | Inside the ability | 42 |
| 56 | TH-21 | Inside the ability | 20 |
| 57 | VO-36 | Inside the ability | 20 |
| 58 | VO-37 | Inside the ability | 28 |
| 59 | VO-38 | Inside the ability | 20 |
| 60 | VO-39 | Inside the ability | 53 |
| 61 | VO-40 | Inside the ability | 61 |
| 62 | VO-41 | Inside the ability | 51 |
| 63 | TH-22 | Inside the ability | 82 |
| 64 | TH-23 | End screen | 47 |

---

## 4. Judgement calls

**Could have gone either way (put in talking head):**

- **TH-02 and TH-03 (cold open).** Both mention things that could be screen recordings (the Studio app, the GitHub docs), but the script cues the whole cold open as talking head, and the first minute needs your face for retention. The editor can cut away to Studio and GitHub over your audio.
- **TH-06 ("So now we've got a username...").** It sits in a screen section with no cue of its own. It's a transition and the first outing of the "they just sit there" gag, which plays better to camera.
- **TH-10 (CasaGees side hustle).** It's in the middle of the config walkthrough, but it's personal and a nice break from the code. If you'd rather keep the config section as one unbroken voiceover, it works just as well as VO over CasaGees b-roll.
- **TH-14 (the SSH story).** The script puts the terminal transcript and window MG after this paragraph, so parts of it could be VO. I kept the whole story as one talking head take because it's the emotional core of the video and splitting it would break your flow. The editor should cut to the real transcript around "It found my Wordmove config" and back to you for the last line.
- **TH-16 ("Right. We're connected...").** The slot-management screen cue sits just above it, but the line is a section transition that recaps the story so far. The screen cue fits VO-28 better.
- **TH-17 ("The pain in the backside...").** It's opinion and mild frustration, so it goes to camera. The calendar MG lands as it finishes.
- **TH-20 (the confession).** The editor screen cue sits just above this heading, but "I'm not going to lie to you" needs your face. The code walkthrough starts at VO-30.
- **TH-21 ("I'm not going to go through all of this line by line...").** A short aside to camera in the middle of the code. It could stay as VO over the scrolling code if you'd rather not break the walkthrough.

**Went to voiceover even though it has personality:**

- **VO-20 and VO-21 ("Now let's try it" and "Sweet huh!").** Both are spoken to the viewer, but the script cues the screen here and the payoff is watching the response land. Put the energy into your voice.
- **VO-25 (switching back to Subscriber).** It's a responsible little judgement, but the script cues the screen, and seeing the role change back is the proof.
- **VO-27 ("Instructions are a request, whereas permissions are a wall").** It's one of the strongest opinion lines in the video, but the script cues the settings file and the two-layer MG, and that frame is the one people will screenshot. If you record a spare talking head take of just the last two sentences, the editor has the option.

**Lines fixed since the first pass** (the plugin code changed, so the script now matches it):

- **VO-41.** `show_in_rest` has been removed from the code. The line now describes `meta.mcp.public`, which is what the MCP Adapter actually checks.
- **TH-18 and VO-32.** The permission callback now checks a custom `manage_casagees_slots` capability instead of `read`, so "only our claude-ai user can call it" is true and the two clips agree.

**Capability and docblock:** the capability was granted with `wp user add-cap claude-ai manage_casagees_slots`, and VO-32 now says so. The docblock above `casagees_abilities_can_manage` has been updated to match, so it's safe to record the screen.
