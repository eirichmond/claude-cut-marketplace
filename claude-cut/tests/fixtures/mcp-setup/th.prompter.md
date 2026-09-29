# Talking head prompter: Connect Claude Code to WordPress with MCP (Then Lock It Down)
# Generated from mcp-setup.director.json. Read in order; the ## IDs are not spoken.

## b01

### Delivery: Fast, conspiratorial hook; lean on 'over SSH', then a promise to camera.

While I was testing this, Claude Code got into my live WordPress site over SSH, which is not how I'd told it to get in. I'll show you exactly how that happened later, and how to stop it happening to you.

## b02

### Delivery: Conversational; wry pause before and after 'Fine.', then set up your own config.

Okay, so some of you are going to hate this. AI is everywhere, and we're using it in WordPress in all sorts of different ways now. Locally, you can spin up a WordPress site pretty easily with the Studio app and chat to the built-in AI. Fine. But I wanted to set up my own configuration, using Claude Code, talking to a real site.

## b03

### Delivery: Steady, setting up the problem; land 'So that's what this video is.' firmly.

Now, there is official documentation for this. It lives on the WordPress GitHub account under the MCP Adapter repository, and it tells you how to connect your site over MCP. What it doesn't do is walk you through the couple of things you need in place first, or how to actually build the config file. So that's what this video is.

## b04

### Delivery: Relaxed and plain on the definition; knowing smile on 'back pocket'.

For those of you who don't know, MCP stands for Model Context Protocol, and all it really is is a standard way for an AI agent to talk to a piece of software. Keep that in your back pocket, because I'll give you a better analogy in a minute.

## b06b

### Delivery: Firm warning to camera; hit 'admin' and 'let it go wild'.

A lot of the tutorials out there just generate the password on the admin account they're already logged in as, and you really don't want to hand an AI admin and let it go wild on your site doing things you didn't expect.

## b08

### Delivery: Slower; deadpan pause before 'They just sit there.'

So now we've got a username and an application password for our claude-ai user. On their own, they don't give an AI anything useful to work with. They just sit there.

## b11b

### Delivery: Lift on 'that's where the analogy comes in'; lead into the kitchen.

The magic is in how you put them together, and that's where the analogy comes in.

## b12

### Delivery: Slower and warmer; grin on 'I was one once'; land 'The hatch'.

Imagine you're a chef (bear with me, I was one once) and you need to get into the ingredients cupboard. The MCP server is the doorway into that cupboard. The hatch, if you like.

## b13

### Delivery: Explanatory, unhurried; one idea per sentence, pause after each.

Inside the cupboard, all the ingredients are in jars, and those jars are the Abilities API. An ability is a single thing your site can do, described in a way an AI agent can understand, like creating a post, looking up an order or regenerating delivery slots. Nothing is in the cupboard unless somebody has registered it as an ability, and every ability carries a permission check, much like the capabilities your user roles already have.

## b14

### Delivery: Unhurried; land 'That's the whole point of picking the lowest role.' to camera.

So some jars have a padlock on them and some are open, depending on who's asking. Our subscriber user can't reach much, whereas an admin could reach a lot more. That's the whole point of picking the lowest role.

## b15

### Delivery: Deliberate, the main insight; lean in on sentence 44, pause before 'The key is'.

What you really need to understand is that the key to the hatch is not the adapter plugin, and it's not the user with the application password. The key is the MCP configuration on your local machine. That config is what opens the hatch, and the abilities are what's on the shelves once you're in.

## b16a

### Delivery: Straight to camera, a touch of edge on what the docs skip; 'so let's do that'.

The official docs give you a basic config, but they don't tell you where it lives or how to build it, so let's do that.

## b21

### Delivery: Light personal aside, a smile on 'side hustle'.

I'm using the CasaGees site, which is the pizza delivery service we run from home, a little side hustle that keeps me busy at weekends.

## b23b

### Delivery: Serious, to camera; land 'accidentally get committed'.

That way the actual password never ends up in a file that could accidentally get committed.

## b24

### Delivery: Punchy, eyebrow raised on 'numpty'.

Please don't be the numpty who pushes an application password to GitHub.

## b27

### Delivery: Considered; stress 'deliberate choice' at the end.

You could add this to your global Claude configuration so it's available everywhere, but I don't want that. I want the control to sit inside the project, and I only want this server running while I'm actually in the session. When I close the session, the connection closes with it, and that's a deliberate choice.

## b31

### Delivery: Curious, setting up an experiment.

Before we build anything, I want to see what a slightly more privileged role gives me.

## b35

### Delivery: Serious for a second; slower, direct to camera.

Now, remember what I said at the start about SSH? Before I create an ability, I need to show you that, because I found it out the hard way.

## b36

### Delivery: Storytelling, building tension; pause before 'So it went looking for another way in.'

I'm using Claude Code, and it will be sneaky unless you give it some guard rails. In this project I've got config files for pulling and pushing the site, using a Ruby gem called Wordmove. While I was testing, I asked the agent to do something it couldn't do over MCP, because I hadn't created the abilities for it yet. So it went looking for another way in. It found my Wordmove config, used the SSH keys already set up on my machine, and got into the site over SSH. It went straight round the sandbox I thought it was in.

## b37

### Delivery: Firm and practical; 'no SSH and no other route in' spelt out.

So put the rules in writing. Tell the AI, in plain language, that when it's interacting with this site it must only use the MCP connection and the Abilities API, with no SSH and no other route in. That goes in your project's `CLAUDE.md`, or your global one.

## b39b

### Delivery: A grin, short and snappy.

Belt and braces.

## b40

### Delivery: Reset, lighter; upbeat 'Right.' then a beat.

Right. We're connected, we've got guard rails, and apart from what WordPress and WooCommerce already expose, we've got nothing of our own in the cupboard. So let's set some up.

## b41

### Delivery: Personal and relaxed; land 'That's the guard rail for customers.'

On the CasaGees site we run a slot system. We open Thursday, Friday and Saturday, from 5pm til 9pm, and we can only do twelve pizzas in any half-hour slot. When somebody orders, that slot's capacity drops so we never over-commit, and if there are no slots left, nobody can order. That's the guard rail for customers.

## b42

### Delivery: Exasperated, comic; 'every single week' with feeling.

The pain in the backside is that once Saturday evening's slots are done, somebody has to go in and regenerate them for next week, every single week. And if we forget, nobody can order.

## b43

### Delivery: Building enthusiasm; pause, then 'Let's build it.'

So why not expose the slot system to the AI as an ability and let it generate them? I'll register an ability for reading and creating slots, and lock it down with its own capability so only our claude-ai user can call it. Then from Claude Cowork I can set up a skill and a schedule. I do my shifts at the weekend, and come Sunday morning the slots are already sitting there ready for customers, without me having to think about it.

Let's build it.

## b44

### Delivery: Candid, a little sheepish, then matter-of-fact.

Okay, so I'm not going to lie to you. I got AI to build the ability as well. The prompt was something like "build me an ability using the WP Abilities API to read and update order slots", and it went off and built it for me. So what I'm doing here is walking you through the logic it came up with, which lives in its own separate plugin.

## b48

### Delivery: Firm, landing the point; 'only one user has the key'.

Subscribers, customers and even Shop Managers don't have it, so they can't run the ability. That's the padlock on the jar, and only one user has the key.

## b51b

### Delivery: Relaxed aside to camera.

I'm not going to go through all of this line by line, because it's a video in its own right.

## b52

### Delivery: Quick; say the function name over the screen, 'Same padlock' back to camera.

The permission callback is the function we just looked at on the other file, `casagees_abilities_can_manage`. Same padlock, wired in here.

## b53

### Delivery: Plain summary; clear contrast between 'fetches' and 'writes'.

Put simply, we've registered two abilities. One to get the order slots, and one to create them. One goes and fetches the data, the other one writes it.

## b56

### Delivery: The big idea, direct to camera; three even beats, grin on 'Sweet huh!'

That's really what the Abilities API is about. Not just "here's a function", but "here's what it wants, here's what it gives back, and here's who's allowed to call it". Sweet huh!

## b58

### Delivery: Reflective and honest; 'I trust it.' on its own.

Now, although I did get AI to write this, I do understand what it's done, because I know how the Abilities API works. It'll look slightly different for anyone else who writes this logic, or gives it a different prompt, but for my prompt it did a pretty good job and I'm happy to leave it as it is. I trust it. Like I said, maybe I'll come back and do a proper video on the ability itself, because it deserves one.

## b59

### Delivery: Warm sign-off, framed left; leave a beat after 'Happy building.'

If you want the theory behind all this (what the Abilities API actually is and why the official adapter matters), that's in the video on screen now. And if you've already connected an AI to your site, go and check what role it's running as. Happy building.
