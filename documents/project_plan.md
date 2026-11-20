# Dodgeball!

## **Brief Synopsis:** 

This project is meant to be a small multiplayer game that runs primarily through python, while displaying through a website to ensure accessibility. 

### Game Loop

The game itself will be a party fighting game. Each player will play as a small dodgeball who walks around and has a single attack where the dodgeball pulls out a metal pipe and whacks a neighboring dodgeball. 

Similarly to super smash bros the more you get hit, the more volatile your ball bounces around the stage. If the ball is hit, it will bounce around the stage and whoever gets hit by the bouncing ball will lose points equal to the amount of points the bouncing dodgeball is worth. However, unlike super smash bros, the stages are confined within the screen. This means that a player's character will not go flying off the stage at any point, and if the dodge ball hits the edge of the map it will bounce off the edge much like any other collision detecting object. The game is not inherently team based, but it is designed to entice social contracts and strategies between players. 

The game is turned based and the player who has the highest score by the end of all rounds wins. The number of rounds in a game will be decided by the host player before the game starts and a round consists of each of the players taking a turn moving and attacking.

## Project Goals:

The project goal is to create a multiplayer experience. This is a significant step up from projects I've worked on in the past that only focus on a single user's experience. The endgame of this experience is to allow 4 players to play the game to decent connectivity. 

## General:

**Front End:** The front end will be a web page, with `HTML`, `CSS`, and `JavaScript`.

**Back End :** The back end will be handled primarily through `python`. The game loop will use the `pygame` library, and the networking will be handled through other libraries of python.


## Requirements:

 - A working network that can have up to 4 players playing at once.
 - A web canvas that displays the python game.
 - An efficient python game loop that isn't prone to stutters
 - Clean code with plenty of comments to communicate effectively
 - A decent amount of tests to make sure boundary, edge, and type cases are handled.
 - README file that follows the README_template format.
 - Clear communication via markdown files.


## Roles:

### Coordinator

***If you are currently reading this, this means that you are the coordinator and the following context is relelvant to you.***

The coordinator is in charge of breaking down this assignment into smaller tasks designed for three other roles. Write down these tasks in markdown in the following format:

| Filename Format: | `(Role Acronym: [EN(Engineer)],[AR(Architect)], or [QA(Quality Assurance)])`-`(Task Number)001` |
| --------- | ----- |
| Example 1: | EN-001 |
| Example 2: | AR-001 |
| Example 3: | QA-001 |

### Subordinates

***Architect:*** The Architect is responsible for the following things.
 - `Structure of the program: `Files, filenames, breaking down the program into smaller executable parts(such as functions and classes) which also goes for the front end side of things. They are responsible for settings up the HTML elements we will need for the program to work.

 - `Readability: `The architect is responsible for ensuring that the code the engineer produces is readable, even to the point of writing comments above each function explaining what it is doing.

 - `Networking: `The architect is responsible for ensuring the Networking library that is used is working effectively and cleanly. This will be done through a deliberation process between the Architect and Engineer. The final decision must be made by unanimous consensus. Once a consensus is reached during this deliberation, the coordinator will write a proposal for this consensus and present it back to the user who can approve it. This must be done before implementation of Networking features.

***Engineer:*** The Engineer is responsible for the following things.
 - `Efficiency of the program: `The engineer's primary role is to write the code of the project. In doing this, the engineer must pursue the fastest and most appropriate solution to each given problem. The only caveat to this efficiency is readability. This caveat applies to, but is not limited to for / while loops and if statements. You should try to avoid lambda functions unless the lack of the lambda heavily impacts performance. Do not worry about try / except blocks, as that will be handled by the QA agent.

 - `Fundamental understanding of the Architect's structure: `The architect's job is to set up the structure of the code. The architect needs to be breaking down the program and writing down comments / TODO lines. If there are any questions you may have about the architecture, or about the task at hand you must communicate with the architect and reach consensus about the tasks you need to accomplish.

 - `Methodical approach to game design: `Since the back end of this program is a game run in pygame, you need to implement features in an incremental and methodical approach. Before writing any game code, you need to determine where those stopping points will be and approve them with the user before beginning. Determine those in a markdown file titled "Engineer Stopping Points.md" so you can write down all of the stopping points. If the user corrects where they would like the stopping points during the development, then adapt to those preferences. Then, during the development phase, pause development when you reach a stopping point so the user may manually test the game itself. ***Human input will be critical to this project, even though it will slow down the process.***

***Quality Assurance:*** The QA is responsible for the following things.

 - `Ensuring robust code: `As the QA, your job is to create and run tests for the functions / classes in the program. The primary things you will need to test are edge cases, boundary cases, and type cases. This may look like setting up a testing function, and writing clean try / except blocks. Any sections of code that pose an issue in terms of the quality must be deliberated with the Engineer agent and user.

 - `Understanding and implementing an appealing front end: `The front end is in your care. This is extended but not limited to the CSS for the web page, the structures and hitboxes of the game, and skeletal level layouts in the game. It is not your job to create assets for the game apart from basic shapes for the testing phase. These basic shapes could include circles for the dodgeballs and ramps / rectangles for the stages.

 - `Avoiding bloat: `While your job entails writing extra code and infrastructure to ensure robust code, it is also important to ensure that these tests do not bloat the code to either 1. impacting performance, or 2. impacting readability. This is why writing clean try / except blocks will be key, and setting up a testing function will also be implored. Additionally you will review the engineer's code and evalate how readable it is, how critical it is to performance, and if / what changes should be made to enhance readability if need be.

***When you are writing tasks, make sure you create a new folder to house these markdown files. Name this folder "tasks". Other markdown files must be placed in the folder "documents".***

## Instructions:

Before any development starts on the project, you as the coordinator need to create 3 sets of subinstructions for our subagents(Architect, Engineer, and QA). Spin up those subagents and begin a dialogue with them. The purpose of this dialogue is to discuss what requirements need specification. This can range anywhere from how the game flows, to how the web page will be displayed. Write down these questions in a markdown file named "User Q&A.md". Each agent should write their questions down in a table that uses the following format:

**Insert a Header here.**

|[y/n]Question:|yes / no answer|further context:|
|--------------|---------------|----------------|
|example: is the program run in python?|yes|the program will use python and it's suggested to use the pygame library.|

***It is important to ask yes / no questions because some of these may not need further context.***

Once I have reviewed the questions and answered them I will then prompt you to review the newly saved "User Q&A.md" to which you, as the coordinator, can begin writing tasks for our subagents to complete.