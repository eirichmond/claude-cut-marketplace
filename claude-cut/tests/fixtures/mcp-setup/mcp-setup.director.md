# Director: Connect Claude Code to WordPress with MCP (Then Lock It Down)

_Rendered from `mcp-setup.director.json`. Don't edit this file; edit the JSON and re-render._

**33 talking head segments (about 1372 words, roughly 9:09 spoken) and 32 voiceover segments (about 1170 words, roughly 7:48 spoken).**

---

## 1. Talking head shot list

### Cold open

**b01**

> While I was testing this, Claude Code got into my live WordPress site over SSH, which is not how I'd told it to get in. I'll show you exactly how that happened later, and how to stop it happening to you.

*Delivery:* Fast, conspiratorial hook; lean on 'over SSH', then a promise to camera.

**b02**

> Okay, so some of you are going to hate this. AI is everywhere, and we're using it in WordPress in all sorts of different ways now. Locally, you can spin up a WordPress site pretty easily with the Studio app and chat to the built-in AI. Fine. But I wanted to set up my own configuration, using Claude Code, talking to a real site.

*Delivery:* Conversational; wry pause before and after 'Fine.', then set up your own config.

**b03**

> Now, there is official documentation for this. It lives on the WordPress GitHub account under the MCP Adapter repository, and it tells you how to connect your site over MCP. What it doesn't do is walk you through the couple of things you need in place first, or how to actually build the config file. So that's what this video is.

*Delivery:* Steady, setting up the problem; land 'So that's what this video is.' firmly.

**b04**

> For those of you who don't know, MCP stands for Model Context Protocol, and all it really is is a standard way for an AI agent to talk to a piece of software. Keep that in your back pocket, because I'll give you a better analogy in a minute.

*Delivery:* Relaxed and plain on the definition; knowing smile on 'back pocket'.

### Step one: a user with the lowest possible role

**b06b**

> A lot of the tutorials out there just generate the password on the admin account they're already logged in as, and you really don't want to hand an AI admin and let it go wild on your site doing things you didn't expect.

*Delivery:* Firm warning to camera; hit 'admin' and 'let it go wild'.

### Step two: an application password

**b08**

> So now we've got a username and an application password for our claude-ai user. On their own, they don't give an AI anything useful to work with. They just sit there.

*Delivery:* Slower; deadpan pause before 'They just sit there.'

### Step three: install the MCP Adapter

**b11b**

> The magic is in how you put them together, and that's where the analogy comes in.

*Delivery:* Lift on 'that's where the analogy comes in'; lead into the kitchen.

### The hatch and the cupboard

**b12**

> Imagine you're a chef (bear with me, I was one once) and you need to get into the ingredients cupboard. The MCP server is the doorway into that cupboard. The hatch, if you like.

*Delivery:* Slower and warmer; grin on 'I was one once'; land 'The hatch'.

**b13**

> Inside the cupboard, all the ingredients are in jars, and those jars are the Abilities API. An ability is a single thing your site can do, described in a way an AI agent can understand, like creating a post, looking up an order or regenerating delivery slots. Nothing is in the cupboard unless somebody has registered it as an ability, and every ability carries a permission check, much like the capabilities your user roles already have.

*Delivery:* Explanatory, unhurried; one idea per sentence, pause after each.

*Bed:* `b13.mg1` MG, bed, to "those jars are the Abilities API": Kitchen illustration continues: the cupboard opens to reveal shelves of labelled jars; caption 'Jars = abilities (Abilities API)'. Back to face for sentence 39.

**b14**

> So some jars have a padlock on them and some are open, depending on who's asking. Our subscriber user can't reach much, whereas an admin could reach a lot more. That's the whole point of picking the lowest role.

*Delivery:* Unhurried; land 'That's the whole point of picking the lowest role.' to camera.

*Bed:* `b14.mg1` MG, bed, to "an admin could reach a lot more": Kitchen illustration: padlocks click on to some jars, others stay open. A small 'Subscriber' tag by the chef can reach only a couple of jars; swap to an 'Admin' tag and most jars light up. Back to face for sentence 43.

**b15**

> What you really need to understand is that the key to the hatch is not the adapter plugin, and it's not the user with the application password. The key is the MCP configuration on your local machine. That config is what opens the hatch, and the abilities are what's on the shelves once you're in.

*Delivery:* Deliberate, the main insight; lean in on sentence 44, pause before 'The key is'.

### Step four: the MCP config file

**b16a**

> The official docs give you a basic config, but they don't tell you where it lives or how to build it, so let's do that.

*Delivery:* Straight to camera, a touch of edge on what the docs skip; 'so let's do that'.

**b21**

> I'm using the CasaGees site, which is the pizza delivery service we run from home, a little side hustle that keeps me busy at weekends.

*Delivery:* Light personal aside, a smile on 'side hustle'.

**b23b**

> That way the actual password never ends up in a file that could accidentally get committed.

*Delivery:* Serious, to camera; land 'accidentally get committed'.

**b24**

> Please don't be the numpty who pushes an application password to GitHub.

*Delivery:* Punchy, eyebrow raised on 'numpty'.

### Step five: fire it up

**b27**

> You could add this to your global Claude configuration so it's available everywhere, but I don't want that. I want the control to sit inside the project, and I only want this server running while I'm actually in the session. When I close the session, the connection closes with it, and that's a deliberate choice.

*Delivery:* Considered; stress 'deliberate choice' at the end.

### Quick test: what can it actually see?

**b31**

> Before we build anything, I want to see what a slightly more privileged role gives me.

*Delivery:* Curious, setting up an experiment.

### Put the guard rails up first

**b35**

> Now, remember what I said at the start about SSH? Before I create an ability, I need to show you that, because I found it out the hard way.

*Delivery:* Serious for a second; slower, direct to camera.

**b36**

> I'm using Claude Code, and it will be sneaky unless you give it some guard rails. In this project I've got config files for pulling and pushing the site, using a Ruby gem called Wordmove. While I was testing, I asked the agent to do something it couldn't do over MCP, because I hadn't created the abilities for it yet. So it went looking for another way in. It found my Wordmove config, used the SSH keys already set up on my machine, and got into the site over SSH. It went straight round the sandbox I thought it was in.

*Delivery:* Storytelling, building tension; pause before 'So it went looking for another way in.'

**b37**

> So put the rules in writing. Tell the AI, in plain language, that when it's interacting with this site it must only use the MCP connection and the Abilities API, with no SSH and no other route in. That goes in your project's `CLAUDE.md`, or your global one.

*Delivery:* Firm and practical; 'no SSH and no other route in' spelt out.

**b39b**

> Belt and braces.

*Delivery:* A grin, short and snappy.

### Now the abilities

**b40**

> Right. We're connected, we've got guard rails, and apart from what WordPress and WooCommerce already expose, we've got nothing of our own in the cupboard. So let's set some up.

*Delivery:* Reset, lighter; upbeat 'Right.' then a beat.

**b41**

> On the CasaGees site we run a slot system. We open Thursday, Friday and Saturday, from 5pm til 9pm, and we can only do twelve pizzas in any half-hour slot. When somebody orders, that slot's capacity drops so we never over-commit, and if there are no slots left, nobody can order. That's the guard rail for customers.

*Delivery:* Personal and relaxed; land 'That's the guard rail for customers.'

**b42**

> The pain in the backside is that once Saturday evening's slots are done, somebody has to go in and regenerate them for next week, every single week. And if we forget, nobody can order.

*Delivery:* Exasperated, comic; 'every single week' with feeling.

**b43**

> So why not expose the slot system to the AI as an ability and let it generate them? I'll register an ability for reading and creating slots, and lock it down with its own capability so only our claude-ai user can call it. Then from Claude Cowork I can set up a skill and a schedule. I do my shifts at the weekend, and come Sunday morning the slots are already sitting there ready for customers, without me having to think about it.
> Let's build it.

*Delivery:* Building enthusiasm; pause, then 'Let's build it.'

### Confession time: I got AI to build the ability too

**b44**

> Okay, so I'm not going to lie to you. I got AI to build the ability as well. The prompt was something like "build me an ability using the WP Abilities API to read and update order slots", and it went off and built it for me. So what I'm doing here is walking you through the logic it came up with, which lives in its own separate plugin.

*Delivery:* Candid, a little sheepish, then matter-of-fact.

**b48**

> Subscribers, customers and even Shop Managers don't have it, so they can't run the ability. That's the padlock on the jar, and only one user has the key.

*Delivery:* Firm, landing the point; 'only one user has the key'.

### Inside the ability

**b51b**

> I'm not going to go through all of this line by line, because it's a video in its own right.

*Delivery:* Relaxed aside to camera.

**b52**

> The permission callback is the function we just looked at on the other file, `casagees_abilities_can_manage`. Same padlock, wired in here.

*Delivery:* Quick; say the function name over the screen, 'Same padlock' back to camera.

*Bed:* `b52.sr1` SR, bed, to "casagees_abilities_can_manage": Editor: the permission_callback argument set to casagees_abilities_can_manage, highlighted. *(reanchored, see below)*

**b53**

> Put simply, we've registered two abilities. One to get the order slots, and one to create them. One goes and fetches the data, the other one writes it.

*Delivery:* Plain summary; clear contrast between 'fetches' and 'writes'.

**b56**

> That's really what the Abilities API is about. Not just "here's a function", but "here's what it wants, here's what it gives back, and here's who's allowed to call it". Sweet huh!

*Delivery:* The big idea, direct to camera; three even beats, grin on 'Sweet huh!'

**b58**

> Now, although I did get AI to write this, I do understand what it's done, because I know how the Abilities API works. It'll look slightly different for anyone else who writes this logic, or gives it a different prompt, but for my prompt it did a pretty good job and I'm happy to leave it as it is. I trust it. Like I said, maybe I'll come back and do a proper video on the ability itself, because it deserves one.

*Delivery:* Reflective and honest; 'I trust it.' on its own.

### End screen

**b59**

> If you want the theory behind all this (what the Abilities API actually is and why the official adapter matters), that's in the video on screen now. And if you've already connected an AI to your site, go and check what role it's running as. Happy building.

*Delivery:* Warm sign-off, framed left; leave a beat after 'Happy building.'

---

## 2. Voiceover shot list

### Step one: a user with the lowest possible role

**b05**

> The first thing to do happens on your live production site, not your local one, because we're going to connect local to production and interrogate the real thing. So on your live site, create a new user. I've called mine claude-ai, and I've given it a password I'm probably never going to log in with (which doesn't matter for this connection anyway).

*Delivery:* Brisk, instructional; stress 'live production site, not your local one'.

*On screen:* Live wp-admin, Users > Add New, creating claude-ai (password and email blurred).

*Bed:* `b05.sr1` SR, bed: Live production wp-admin (address bar visible): Users > Add New. Type username claude-ai, fill email, set a password. Leave the role dropdown for the next beat.

**b06a**

> The important bit is the role. Set it to the lowest possible, which is Subscriber.

*Delivery:* Slow down on 'The important bit is the role.', beat, then 'Subscriber'.

*On screen:* Role dropdown opened and set to Subscriber, punch in.

*Bed:* `b06.sr1` SR, bed, segment: Same Add New screen: open the Role dropdown and choose Subscriber. Cut back to face for sentence 19. *(reanchored, see below)*

### Step two: an application password

**b07**

> Next, on that same user, scroll down to Application Passwords and generate one. If you've not come across these, an application password is a separate credential that lets a piece of software talk to your site without using your actual login. Give it a name, hit the button, and WordPress generates it for you and shows it once, so copy it somewhere safe because you won't see it again.

*Delivery:* Brisk; small breath before the definition; stress 'shows it once'.

*On screen:* claude-ai profile, Application Passwords, generating one (password blurred).

*Bed:* `b07.sr1` SR, bed: Edit the claude-ai user, scroll down to Application Passwords, type a name (e.g. 'Claude Code'), click Add New Application Password, show the generated password box and the copy action.

### Step three: install the MCP Adapter

**b09**

> Now install the official WordPress MCP Adapter plugin. As far as I know it's being assessed for the WordPress plugin directory, but at the moment it doesn't live there. It lives on GitHub under the official WordPress account, in a repo called `mcp-adapter`, and the link is in the description.

*Delivery:* Brisk; light hedge on 'as far as I know'; clear on 'mcp-adapter'.

*On screen:* github.com/WordPress/mcp-adapter repo home, README header.

*Bed:* `b09.sr1` SR, bed: github.com/WordPress/mcp-adapter repo home: the WordPress org name and repo name clearly visible, scroll the README header.

**b10**

> The easiest way in is the Releases page on that repo, where there's a ready-made `mcp-adapter.zip` to download. Upload that through Plugins, Add New, on your live site, and activate it. (If you'd rather build it yourself, you can clone the repo and build the zip, but for a live site I'd stick with the tagged release.)

*Delivery:* Brisk and practical; drop the voice slightly for the bracketed aside.

*On screen:* Releases page, mcp-adapter.zip download, then Plugins > Add New > Upload > Activate.

*Bed:* `b10.sr1` SR, bed: Repo Releases page: latest tagged release, Assets list, click mcp-adapter.zip to download. Then live wp-admin: Plugins > Add New > Upload Plugin, choose the zip, Install Now, Activate. Show the plugin listed as active.

**b11a**

> Again, on its own, it just sits there. A user with an application password does nothing, and having the adapter installed does nothing.

*Delivery:* Measured; a small pause between each thing that 'does nothing'.

*On screen:* Three greyed-out icons appear one by one: user, key, plugin.

*Bed:* `b11.mg1` MG, bed, segment: Three icons appear one at a time, each greyed out: a user icon (on 'A user'), a key icon (on 'application password'), a plugin icon (on 'adapter installed'). No labels needed beyond small captions 'User', 'App password', 'MCP Adapter'. Cut back to face for sentence 34. *(reanchored, see below)*

### Step four: the MCP config file

**b16b**

> In your local project folder, create a file called `.mcp.json`, which is just a JSON object.

*Delivery:* Clear and methodical; spell out 'dot mcp dot json'.

*On screen:* Editor at the project root: New File .mcp.json, {} typed.

*Bed:* `b16.sr1` SR, bed: Code editor, file explorer at the project root: New File, name it .mcp.json, empty file open with {} typed. *(reanchored, see below)*

**b17**

> From the MCP adapter GitHub docs, you can just copy this object directly into your .mcp.json file.

*Delivery:* Quick, matter-of-fact.

*On screen:* MCP Adapter docs example config copied and pasted into .mcp.json.

*Bed:* `b17.sr1` SR, bed: MCP Adapter repo docs (the CLI usage guide) showing the example config object; copy it, switch to the editor and paste into .mcp.json.

**b18**

> At the top level we need an `mcpServers` object. You can set up multiple servers in here, but this is the bare minimum. Inside that, create an object named after the connection. I've called mine `claude-ai` to match the user.

*Delivery:* Methodical, one idea per line; short pause between keys.

*On screen:* mcpServers key, then the claude-ai object highlighted as mentioned.

*Bed:* `b18.sr1` SR, bed: Editor, large font. Build (or highlight) line by line as described: the top-level "mcpServers" key highlighted on sentence 50, then the "claude-ai" object inside it highlighted on sentence 52. Each key gets a soft highlight box as it's mentioned.

**b19**

> Now the guts of it. `command` is `npx`, and `args` is an array with `-y` and then `@automattic/mcp-wordpress-remote@latest`. That's the little bridge that runs on your machine and talks to the adapter on your site.

*Delivery:* Methodical; read the package name slowly and clearly.

*On screen:* command and args lines highlighted, then the bridge flow graphic.

*Bed:* `b19.sr1` SR, bed: Editor: "command": "npx" then "args": ["-y", "@automattic/mcp-wordpress-remote@latest"], each key highlighted as it's said.

**b20**

> Then the environment variables. `WP_API_URL` is your site, followed by the route to the hatch, which is `/wp-json/mcp/mcp-adapter-default-server`. That's the address the agent goes looking for.

*Delivery:* Slow right down on the route; people get it wrong.

*On screen:* env object, WP_API_URL with the route, punch in on the route.

*Bed:* `b20.sr1` SR, bed: Editor: "env" object added, "WP_API_URL" typed with the site domain followed by /wp-json/mcp/mcp-adapter-default-server, keys highlighted as mentioned.

**b22**

> `WP_API_USERNAME` is the user you created, and `WP_API_PASSWORD` is the application password WordPress generated for it.

*Delivery:* Methodical; clear gap between the two keys.

*On screen:* WP_API_USERNAME and WP_API_PASSWORD keys added with ${} values.

*Bed:* `b22.sr1` SR, bed: Editor: "WP_API_USERNAME" and "WP_API_PASSWORD" keys typed, each highlighted as mentioned. Values typed as ${WP_API_USERNAME} and ${WP_API_PASSWORD}, never the real ones.

**b23a**

> Now, for security reasons, I haven't pasted the real values in here. I've set them as environment variables on my machine and I'm referencing them with a dollar sign and the variable name in curly brackets.

*Delivery:* A touch more serious; slow on 'dollar sign ... curly brackets'.

*On screen:* Finished .mcp.json, ${} values highlighted, punch in, shell callout.

*Bed:* `b23.sr1` SR, bed: Editor: the whole .mcp.json visible, the ${WP_API_USERNAME} and ${WP_API_PASSWORD} values highlighted.

**b25**

> Finally, and just for sanity, there's `LOG_FILE`. Point it at a subfolder of your project. Mine goes to `mcp/logs/mcp-production.log`, and when something goes wrong (and it will), that's where you look.

*Delivery:* Methodical; a wry lift on '(and it will)'.

*On screen:* LOG_FILE line added, mcp/logs folder, then hold on the finished file.

*Bed:* `b25.sr1` SR, bed: Editor: "LOG_FILE": "./mcp/logs/mcp-production.log" added and highlighted; file explorer shows the mcp/logs folder.

### Step five: fire it up

**b26**

> With that in place, start a Claude Code session in the project. The first thing it'll do is ask whether you want to use this MCP server, so say yes.

*Delivery:* Brisk; 'so say yes' light.

*On screen:* Terminal: run claude, approve the claude-ai MCP server.

*Bed:* `b26.sr1` SR, bed: Terminal in the project folder: run claude, the prompt asking whether to use the claude-ai MCP server from .mcp.json appears, choose yes.

**b28**

> Now let's try it. I'm just going to ask the agent, "can you see my site over MCP?"

*Delivery:* Quick; read the question as if typing it.

*On screen:* Claude Code prompt: 'can you see my site over MCP?'

*Bed:* `b28.sr1` SR, bed: Claude Code prompt: type 'can you see my site over MCP?' and press Enter.

**b29**

> And there you go. It comes back with information about the site, so I can confirm it's all connected and running. Sweet huh!

*Delivery:* Small payoff; smile through 'Sweet huh!'

*On screen:* Claude's response with site info, punch in on the site name (details blurred).

*Bed:* `b29.sr1` SR, bed, segment: Claude Code output: the MCP tool call visible, then the response with the site's name, URL and details. Speed-ramp any wait. *(reanchored, see below)*

**b30**

> So, to recap what you actually need: a live site somewhere, a user on it with the minimum role, an application password for that user, and the official MCP Adapter plugin installed. Then in your local project folder, a `.mcp.json` with the `mcpServers` object and an entry for your connection. That's it.

*Delivery:* Brisk recap, a tiny pause after each item; 'That's it.' flat and final.

*On screen:* Recap checklist builds and ticks item by item.

*Bed:* `b30.mg1` MG, bed, segment: Checklist builds as each item is read, a tick on each: 'A live site', 'A user with the minimum role', 'An application password for that user', 'The MCP Adapter plugin installed', '.mcp.json with mcpServers and your connection'. Back to face for 'That's it.' *(reanchored, see below)*

### Quick test: what can it actually see?

**b32**

> CasaGees runs on WooCommerce, so I'm going to bump the claude-ai user up from Subscriber to Shop Manager and see what comes back.

*Delivery:* Brisk.

*On screen:* claude-ai role changed from Subscriber to Shop Manager, punch in.

*Bed:* `b32.sr1` SR, bed: Live wp-admin: edit the claude-ai user, change Role from Subscriber to Shop Manager, Update User.

**b33**

> So now I can ask things like how many orders were processed this week, or what orders are coming up, and that kind of works. Granted, it's only reading, but it shows the padlocks coming off the jars as the role changes, which is exactly what you'd expect.

*Delivery:* Brisk; slightly wry on 'that kind of works'.

*On screen:* Order questions in Claude Code with MCP tool calls (blurred), then padlocks drop off.

*Bed:* `b33.sr1` SR, bed: Claude Code: ask how many orders were processed this week, then what orders are coming up. Show the MCP tool calls and the answers. Speed-ramp the waits.

**b34**

> And I'm putting it straight back to Subscriber afterwards, because I only needed it for the test.

*Delivery:* Matter-of-fact.

*On screen:* claude-ai role back to Subscriber, 'User updated' notice.

*Bed:* `b34.sr1` SR, bed: Live wp-admin: edit the claude-ai user, Role back to Subscriber, Update User, the 'User updated' notice visible.

### Put the guard rails up first

**b38**

> Then back it up with actual permissions in the hidden `.claude` folder, in `settings.local.json`, where you can deny things like SSH commands outright.

*Delivery:* Practical; stress 'deny' and 'outright'.

*On screen:* .claude/settings.local.json with the deny rules, punch in.

*Bed:* `b38.sr1` SR, bed: Editor: the hidden .claude folder expanded in the explorer, settings.local.json open with a permissions deny list blocking SSH and the other ways in (e.g. ssh, scp, rsync and wordmove commands). Check the exact syntax against the current Claude Code docs.

**b39a**

> Instructions are a request, whereas permissions are a wall, so use both.

*Delivery:* Punchy contrast: 'a request' versus 'a wall'.

*On screen:* Two layers: CLAUDE.md asks nicely, settings deny actually stops it.

*Bed:* `b39.mg1` MG, bed, segment: Two stacked layers: top 'CLAUDE.md = asks nicely', bottom 'settings deny = actually stops it' as a solid wall. Back to face for 'Belt and braces.' *(reanchored, see below)*

### Confession time: I got AI to build the ability too

**b45**

> Let's start with the main plugin file. Up top we've got the usual bits defined, the version and the plugin directory. Then we register an abilities category. Think of that as the shelf in the cupboard. Every ability I add to this site from now on goes on that shelf, so as the list grows it stays organised.

*Delivery:* Steady walkthrough; lift on 'the shelf in the cupboard'.

*On screen:* Abilities plugin main file: header constants, then the category registration.

*Bed:* `b45.sr1` SR, bed: Editor: the abilities plugin's main PHP file. Scroll from the plugin header and defined constants (version, plugin directory) to the abilities category registration; highlight each as it's mentioned.

**b46**

> Below that is where the order slots ability gets registered, hooked into the Abilities API. The ability itself isn't in this file though. It lives in a separate folder called abilities, and we'll have a look at that in a second.

*Delivery:* Steady walkthrough.

*On screen:* Ability registration hook, then the abilities folder in the explorer.

*Bed:* `b46.sr1` SR, bed: Editor: same file, the hook that registers the order slots ability, then the line that loads it from the abilities folder; flick the explorer to show the abilities folder.

**b47**

> The last thing in here is a function called `casagees_abilities_can_manage`. That's the permission callback. It checks whether the current user has a capability called `manage_casagees_slots`, which I've made up for this plugin and given to the claude-ai user and nobody else. I added it from the terminal with WP-CLI (`wp user add-cap claude-ai manage_casagees_slots`), so it sits on that one user rather than a whole role.

*Delivery:* Slightly slower on the capability name; read the command clearly.

*On screen:* casagees_abilities_can_manage() callback, then the wp user add-cap terminal.

*Bed:* `b47.sr1` SR, bed: Editor: the casagees_abilities_can_manage() function at the bottom of the main file, the current_user_can( 'manage_casagees_slots' ) check highlighted.

### Inside the ability

**b49**

> Now for the ability itself. First thing you'll see is an array called the slot schema, which is what we'll hand to the Abilities API when we register.

*Delivery:* Walkthrough, even pace.

*On screen:* Order slots ability file open on the slot schema array.

*Bed:* `b49.sr1` SR, bed: Editor: open the abilities folder, the order slots ability file, land on the slot schema array at the top.

**b50**

> Registering an ability works like this. You give it a namespaced name, something like `casagees/get-order-slots`, and then an array of arguments. Most of them are self-explanatory. A label, a description, the category we set up a minute ago. Then the two that matter.

*Delivery:* Walkthrough; small lift on 'Then the two that matter.'

*On screen:* Register call: casagees/get-order-slots, label, description, category.

*Bed:* `b50.sr1` SR, bed: Editor: the ability registration call, the name 'casagees/get-order-slots', then label, description and category highlighted in turn as they're mentioned.

**b51a**

> The execute callback is all of the logic the ability can actually do. In this case it's interrogating the database, working out what slots exist, and taking in any parameters the AI has passed along so it's got something to reason with.

*Delivery:* Walkthrough, steady through the list of what it does.

*On screen:* execute_callback, scrolling through the database queries.

*Bed:* `b51.sr1` SR, bed, segment: Editor: the execute_callback argument, then scroll through the callback's database queries and parameter handling. Back to face for sentence 142. *(reanchored, see below)*

**b54**

> Let me give you a quick overview of the get ability, because there are two parts we've not covered yet.
> The input schema is what the ability expects to be asked. It's the shape of my question, if you like. Things like dates, whether I'm asking about availability, any limits on how much to return. If I ask the AI something that doesn't fit the schema, it knows it can't use this jar.

*Delivery:* Explanatory, unhurried; pause after the first sentence.

*On screen:* Get ability's input_schema; date, availability and limit properties highlighted.

*Bed:* `b54.sr1` SR, bed: Editor: the get ability, input_schema highlighted; point at the date, availability and limit properties as they're mentioned.

**b55**

> The output schema is the shape of the answer. The AI takes my input, runs the ability, and gets structured data back that it already knows how to read.

*Delivery:* Explanatory.

*On screen:* output_schema highlighted, scrolling its properties.

*Bed:* `b55.sr1` SR, bed: Editor: output_schema highlighted, scroll through its properties.

**b57**

> One more important bit. In the ability's meta there's an `mcp` array with `public` set to true. Abilities are private by default, so without that the ability is registered but the MCP Adapter won't expose it, and your AI will never see the jar on the shelf. Easy one to miss.

*Delivery:* Slightly slower, a heads-up; 'Easy one to miss.' dry.

*On screen:* Ability meta array, 'mcp' => array( 'public' => true ) highlighted.

*Bed:* `b57.sr1` SR, bed: Editor: the ability's meta array with 'mcp' => array( 'public' => true ) highlighted.

---

## 3. Running order

| # | Segment | Mode | Section | Words |
|---|---|---|---|---|
| 1 | b01 | TH | Cold open | 41 |
| 2 | b02 | TH | Cold open | 64 |
| 3 | b03 | TH | Cold open | 61 |
| 4 | b04 | TH | Cold open | 49 |
| 5 | b05 | VO | Step one: a user with the lowest possible role | 62 |
| 6 | b06a | VO | Step one: a user with the lowest possible role | 15 |
| 7 | b06b | TH | Step one: a user with the lowest possible role | 43 |
| 8 | b07 | VO | Step two: an application password | 69 |
| 9 | b08 | TH | Step two: an application password | 31 |
| 10 | b09 | VO | Step three: install the MCP Adapter | 50 |
| 11 | b10 | VO | Step three: install the MCP Adapter | 57 |
| 12 | b11a | VO | Step three: install the MCP Adapter | 23 |
| 13 | b11b | TH | Step three: install the MCP Adapter | 16 |
| 14 | b12 | TH | The hatch and the cupboard | 34 |
| 15 | b13 | TH | The hatch and the cupboard | 76 |
| 16 | b14 | TH | The hatch and the cupboard | 39 |
| 17 | b15 | TH | The hatch and the cupboard | 55 |
| 18 | b16a | TH | Step four: the MCP config file | 25 |
| 19 | b16b | VO | Step four: the MCP config file | 16 |
| 20 | b17 | VO | Step four: the MCP config file | 17 |
| 21 | b18 | VO | Step four: the MCP config file | 40 |
| 22 | b19 | VO | Step four: the MCP config file | 35 |
| 23 | b20 | VO | Step four: the MCP config file | 26 |
| 24 | b21 | TH | Step four: the MCP config file | 25 |
| 25 | b22 | VO | Step four: the MCP config file | 16 |
| 26 | b23a | VO | Step four: the MCP config file | 36 |
| 27 | b23b | TH | Step four: the MCP config file | 16 |
| 28 | b24 | TH | Step four: the MCP config file | 12 |
| 29 | b25 | VO | Step four: the MCP config file | 31 |
| 30 | b26 | VO | Step five: fire it up | 30 |
| 31 | b27 | TH | Step five: fire it up | 55 |
| 32 | b28 | VO | Step five: fire it up | 18 |
| 33 | b29 | VO | Step five: fire it up | 23 |
| 34 | b30 | VO | Step five: fire it up | 52 |
| 35 | b31 | TH | Quick test: what can it actually see? | 16 |
| 36 | b32 | VO | Quick test: what can it actually see? | 23 |
| 37 | b33 | VO | Quick test: what can it actually see? | 48 |
| 38 | b34 | VO | Quick test: what can it actually see? | 17 |
| 39 | b35 | TH | Put the guard rails up first | 29 |
| 40 | b36 | TH | Put the guard rails up first | 101 |
| 41 | b37 | TH | Put the guard rails up first | 48 |
| 42 | b38 | VO | Put the guard rails up first | 23 |
| 43 | b39a | VO | Put the guard rails up first | 12 |
| 44 | b39b | TH | Put the guard rails up first | 3 |
| 45 | b40 | TH | Now the abilities | 30 |
| 46 | b41 | TH | Now the abilities | 57 |
| 47 | b42 | TH | Now the abilities | 34 |
| 48 | b43 | TH | Now the abilities | 86 |
| 49 | b44 | TH | Confession time: I got AI to build the ability too | 69 |
| 50 | b45 | VO | Confession time: I got AI to build the ability too | 58 |
| 51 | b46 | VO | Confession time: I got AI to build the ability too | 41 |
| 52 | b47 | VO | Confession time: I got AI to build the ability too | 66 |
| 53 | b48 | TH | Confession time: I got AI to build the ability too | 28 |
| 54 | b49 | VO | Inside the ability | 28 |
| 55 | b50 | VO | Inside the ability | 43 |
| 56 | b51a | VO | Inside the ability | 42 |
| 57 | b51b | TH | Inside the ability | 20 |
| 58 | b52 | TH | Inside the ability | 20 |
| 59 | b53 | TH | Inside the ability | 28 |
| 60 | b54 | VO | Inside the ability | 73 |
| 61 | b55 | VO | Inside the ability | 29 |
| 62 | b56 | TH | Inside the ability | 32 |
| 63 | b57 | VO | Inside the ability | 51 |
| 64 | b58 | TH | Inside the ability | 82 |
| 65 | b59 | TH | End screen | 47 |

---

## 4. Judgement calls

- **b06a.** Split b06: the role instruction is pure screen, the warning about handing an AI admin is an opinion to camera, which is what the paper edit's visual asks for.
- **b11a.** Split b11 so the icon graphic sits on a clean voiceover and the lead into the analogy is on camera with b12 to b15.
- **b14.** Kept on camera although the padlock graphic covers sentences 41 and 42 (about three quarters of the beat): the analogy section is meant to be warm and on camera, and 'That's the whole point...' has to land to lens.
- **b16a.** Split b16: 'the docs don't tell you where it lives, so let's do that' is a promise to the viewer, so it goes on camera after the chapter card; the bed moves to sentence 48.
- **b21.** Kept on camera (no bed, personal aside) even though it sits between voiceovers; with b23b and b24 this stretch cuts between face and screen every 6 to 20 seconds, which is deliberate for the asides.
- **b23b.** Split b23 so the security point ('never ends up in a file that could accidentally get committed') goes to camera and runs straight into the 'numpty' line, rather than b24 standing alone for five seconds.
- **b29.** The paper edit wants 'Sweet huh!' on camera, but it's a two-word fragment and can't be its own segment, and a cutaway covering 90% of a talking head is really a voiceover. Made it VO with the bed over the whole segment; the b29.sr1 brief still says 'back to face', so the editor can ignore that or drop in a one-second face pop from elsewhere.
- **b30.** Same as b29: 'That's it.' is too short to stand alone, so the whole recap is VO over the checklist, and the b30.mg1 brief's 'back to face' no longer applies.
- **b31.** A single on-camera line (about six seconds) between two runs of voiceover. No bed so it has to be TH; it works as the chapter opener for the Shop Manager test.
- **b37.** Kept on camera; the paper edit's CLAUDE.md screen is an overlay running from 'Tell the AI' to the end of the beat, so only 'So put the rules in writing.' shows the face. Consider whether the paper edit wants that as a bed with a VO sub-beat instead.
- **b39b.** Split b39: 'Belt and braces.' is exactly three words, so it can stand as its own talking-head segment and hands straight into the long on-camera run from b40.
- **b51b.** Split b51 so the 'it's a video in its own right' aside is on camera, as the paper edit's brief asks.
- **b52.** Kept on camera with the code as a timed cutaway so b51b to b53 is one on-camera run of about 30 seconds instead of cutting face, screen, face every eight seconds.

---

## 5. Reanchored beds

Paper-edit bed cues the director moved within their beat, or shortened. The ID and brief are unchanged.

| Cue | Was | Now | Lands on | Reason |
|---|---|---|---|---|
| `b06.sr1` | start of beat, to "which is Subscriber" | sentence 17, whole segment | b06a | b06a is a voiceover now, so the dropdown bed has to cover all of it; the warning in b06b is on camera. |
| `b11.mg1` | start of beat, to "having the adapter installed does nothing" | sentence 32, whole segment | b11a | b11a is a voiceover over the three icons; the lead into the analogy (b11b) is on camera. |
| `b16.sr1` | start of beat | sentence 48 | b16b | b16a went to camera; the editor starts at b16b. |
| `b29.sr1` | start of beat, to "connected and running" | sentence 76, whole segment | b29 | b29 is a voiceover; 'Sweet huh!' is too short to be its own talking-head segment. |
| `b30.mg1` | start of beat, to "an entry for your connection" | sentence 79, whole segment | b30 | b30 is a voiceover; 'That's it.' is too short to be its own talking-head segment. |
| `b39.mg1` | start of beat, to "so use both" | sentence 99, whole segment | b39a | b39a is a voiceover over the two layers; 'Belt and braces.' is on camera in b39b. |
| `b51.sr1` | start of beat, to "something to reason with" | sentence 140, whole segment | b51a | b51a is a voiceover over the execute callback; the aside in b51b is on camera. |
| `b52.sr1` | start of beat, whole segment | sentence 143, to "casagees_abilities_can_manage" | b52 | b52 stays on camera for 'Same padlock, wired in here.'; the code becomes a cutaway ending on the function name. |
