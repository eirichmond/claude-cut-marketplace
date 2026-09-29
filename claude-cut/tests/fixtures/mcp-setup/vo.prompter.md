# Voiceover prompter: Connect Claude Code to WordPress with MCP (Then Lock It Down)
# Generated from mcp-setup.director.json. Read in order; the ## IDs are not spoken.

## b05

### On screen: Live wp-admin, Users > Add New, creating claude-ai (password and email blurred).

### Delivery: Brisk, instructional; stress 'live production site, not your local one'.

The first thing to do happens on your live production site, not your local one, because we're going to connect local to production and interrogate the real thing. So on your live site, create a new user. I've called mine claude-ai, and I've given it a password I'm probably never going to log in with (which doesn't matter for this connection anyway).

## b06a

### On screen: Role dropdown opened and set to Subscriber, punch in.

### Delivery: Slow down on 'The important bit is the role.', beat, then 'Subscriber'.

The important bit is the role. Set it to the lowest possible, which is Subscriber.

## b07

### On screen: claude-ai profile, Application Passwords, generating one (password blurred).

### Delivery: Brisk; small breath before the definition; stress 'shows it once'.

Next, on that same user, scroll down to Application Passwords and generate one. If you've not come across these, an application password is a separate credential that lets a piece of software talk to your site without using your actual login. Give it a name, hit the button, and WordPress generates it for you and shows it once, so copy it somewhere safe because you won't see it again.

## b09

### On screen: github.com/WordPress/mcp-adapter repo home, README header.

### Delivery: Brisk; light hedge on 'as far as I know'; clear on 'mcp-adapter'.

Now install the official WordPress MCP Adapter plugin. As far as I know it's being assessed for the WordPress plugin directory, but at the moment it doesn't live there. It lives on GitHub under the official WordPress account, in a repo called `mcp-adapter`, and the link is in the description.

## b10

### On screen: Releases page, mcp-adapter.zip download, then Plugins > Add New > Upload > Activate.

### Delivery: Brisk and practical; drop the voice slightly for the bracketed aside.

The easiest way in is the Releases page on that repo, where there's a ready-made `mcp-adapter.zip` to download. Upload that through Plugins, Add New, on your live site, and activate it. (If you'd rather build it yourself, you can clone the repo and build the zip, but for a live site I'd stick with the tagged release.)

## b11a

### On screen: Three greyed-out icons appear one by one: user, key, plugin.

### Delivery: Measured; a small pause between each thing that 'does nothing'.

Again, on its own, it just sits there. A user with an application password does nothing, and having the adapter installed does nothing.

## b16b

### On screen: Editor at the project root: New File .mcp.json, {} typed.

### Delivery: Clear and methodical; spell out 'dot mcp dot json'.

In your local project folder, create a file called `.mcp.json`, which is just a JSON object.

## b17

### On screen: MCP Adapter docs example config copied and pasted into .mcp.json.

### Delivery: Quick, matter-of-fact.

From the MCP adapter GitHub docs, you can just copy this object directly into your .mcp.json file.

## b18

### On screen: mcpServers key, then the claude-ai object highlighted as mentioned.

### Delivery: Methodical, one idea per line; short pause between keys.

At the top level we need an `mcpServers` object. You can set up multiple servers in here, but this is the bare minimum. Inside that, create an object named after the connection. I've called mine `claude-ai` to match the user.

## b19

### On screen: command and args lines highlighted, then the bridge flow graphic.

### Delivery: Methodical; read the package name slowly and clearly.

Now the guts of it. `command` is `npx`, and `args` is an array with `-y` and then `@automattic/mcp-wordpress-remote@latest`. That's the little bridge that runs on your machine and talks to the adapter on your site.

## b20

### On screen: env object, WP_API_URL with the route, punch in on the route.

### Delivery: Slow right down on the route; people get it wrong.

Then the environment variables. `WP_API_URL` is your site, followed by the route to the hatch, which is `/wp-json/mcp/mcp-adapter-default-server`. That's the address the agent goes looking for.

## b22

### On screen: WP_API_USERNAME and WP_API_PASSWORD keys added with ${} values.

### Delivery: Methodical; clear gap between the two keys.

`WP_API_USERNAME` is the user you created, and `WP_API_PASSWORD` is the application password WordPress generated for it.

## b23a

### On screen: Finished .mcp.json, ${} values highlighted, punch in, shell callout.

### Delivery: A touch more serious; slow on 'dollar sign ... curly brackets'.

Now, for security reasons, I haven't pasted the real values in here. I've set them as environment variables on my machine and I'm referencing them with a dollar sign and the variable name in curly brackets.

## b25

### On screen: LOG_FILE line added, mcp/logs folder, then hold on the finished file.

### Delivery: Methodical; a wry lift on '(and it will)'.

Finally, and just for sanity, there's `LOG_FILE`. Point it at a subfolder of your project. Mine goes to `mcp/logs/mcp-production.log`, and when something goes wrong (and it will), that's where you look.

## b26

### On screen: Terminal: run claude, approve the claude-ai MCP server.

### Delivery: Brisk; 'so say yes' light.

With that in place, start a Claude Code session in the project. The first thing it'll do is ask whether you want to use this MCP server, so say yes.

## b28

### On screen: Claude Code prompt: 'can you see my site over MCP?'

### Delivery: Quick; read the question as if typing it.

Now let's try it. I'm just going to ask the agent, "can you see my site over MCP?"

## b29

### On screen: Claude's response with site info, punch in on the site name (details blurred).

### Delivery: Small payoff; smile through 'Sweet huh!'

And there you go. It comes back with information about the site, so I can confirm it's all connected and running. Sweet huh!

## b30

### On screen: Recap checklist builds and ticks item by item.

### Delivery: Brisk recap, a tiny pause after each item; 'That's it.' flat and final.

So, to recap what you actually need: a live site somewhere, a user on it with the minimum role, an application password for that user, and the official MCP Adapter plugin installed. Then in your local project folder, a `.mcp.json` with the `mcpServers` object and an entry for your connection. That's it.

## b32

### On screen: claude-ai role changed from Subscriber to Shop Manager, punch in.

### Delivery: Brisk.

CasaGees runs on WooCommerce, so I'm going to bump the claude-ai user up from Subscriber to Shop Manager and see what comes back.

## b33

### On screen: Order questions in Claude Code with MCP tool calls (blurred), then padlocks drop off.

### Delivery: Brisk; slightly wry on 'that kind of works'.

So now I can ask things like how many orders were processed this week, or what orders are coming up, and that kind of works. Granted, it's only reading, but it shows the padlocks coming off the jars as the role changes, which is exactly what you'd expect.

## b34

### On screen: claude-ai role back to Subscriber, 'User updated' notice.

### Delivery: Matter-of-fact.

And I'm putting it straight back to Subscriber afterwards, because I only needed it for the test.

## b38

### On screen: .claude/settings.local.json with the deny rules, punch in.

### Delivery: Practical; stress 'deny' and 'outright'.

Then back it up with actual permissions in the hidden `.claude` folder, in `settings.local.json`, where you can deny things like SSH commands outright.

## b39a

### On screen: Two layers: CLAUDE.md asks nicely, settings deny actually stops it.

### Delivery: Punchy contrast: 'a request' versus 'a wall'.

Instructions are a request, whereas permissions are a wall, so use both.

## b45

### On screen: Abilities plugin main file: header constants, then the category registration.

### Delivery: Steady walkthrough; lift on 'the shelf in the cupboard'.

Let's start with the main plugin file. Up top we've got the usual bits defined, the version and the plugin directory. Then we register an abilities category. Think of that as the shelf in the cupboard. Every ability I add to this site from now on goes on that shelf, so as the list grows it stays organised.

## b46

### On screen: Ability registration hook, then the abilities folder in the explorer.

### Delivery: Steady walkthrough.

Below that is where the order slots ability gets registered, hooked into the Abilities API. The ability itself isn't in this file though. It lives in a separate folder called abilities, and we'll have a look at that in a second.

## b47

### On screen: casagees_abilities_can_manage() callback, then the wp user add-cap terminal.

### Delivery: Slightly slower on the capability name; read the command clearly.

The last thing in here is a function called `casagees_abilities_can_manage`. That's the permission callback. It checks whether the current user has a capability called `manage_casagees_slots`, which I've made up for this plugin and given to the claude-ai user and nobody else. I added it from the terminal with WP-CLI (`wp user add-cap claude-ai manage_casagees_slots`), so it sits on that one user rather than a whole role.

## b49

### On screen: Order slots ability file open on the slot schema array.

### Delivery: Walkthrough, even pace.

Now for the ability itself. First thing you'll see is an array called the slot schema, which is what we'll hand to the Abilities API when we register.

## b50

### On screen: Register call: casagees/get-order-slots, label, description, category.

### Delivery: Walkthrough; small lift on 'Then the two that matter.'

Registering an ability works like this. You give it a namespaced name, something like `casagees/get-order-slots`, and then an array of arguments. Most of them are self-explanatory. A label, a description, the category we set up a minute ago. Then the two that matter.

## b51a

### On screen: execute_callback, scrolling through the database queries.

### Delivery: Walkthrough, steady through the list of what it does.

The execute callback is all of the logic the ability can actually do. In this case it's interrogating the database, working out what slots exist, and taking in any parameters the AI has passed along so it's got something to reason with.

## b54

### On screen: Get ability's input_schema; date, availability and limit properties highlighted.

### Delivery: Explanatory, unhurried; pause after the first sentence.

Let me give you a quick overview of the get ability, because there are two parts we've not covered yet.

The input schema is what the ability expects to be asked. It's the shape of my question, if you like. Things like dates, whether I'm asking about availability, any limits on how much to return. If I ask the AI something that doesn't fit the schema, it knows it can't use this jar.

## b55

### On screen: output_schema highlighted, scrolling its properties.

### Delivery: Explanatory.

The output schema is the shape of the answer. The AI takes my input, runs the ability, and gets structured data back that it already knows how to read.

## b57

### On screen: Ability meta array, 'mcp' => array( 'public' => true ) highlighted.

### Delivery: Slightly slower, a heads-up; 'Easy one to miss.' dry.

One more important bit. In the ability's meta there's an `mcp` array with `public` set to true. Abilities are private by default, so without that the ability is registered but the MCP Adapter won't expose it, and your AI will never see the jar on the shelf. Easy one to miss.
