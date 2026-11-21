# User Q&A

Please answer each question with **yes** or **no** in the answer column. Add clarifying details in the final column where needed. These answers are the pre-development requirements gate.

## Architect Questions

| [y/n] Question | Yes / no answer | Further context |
|---|---|---|
| Should the project use separate Python modules for game state, entities, rules, networking, and startup? | yes | we should only use python modules for states if they work better than pygame. The final decision needs more deliberation. |
| Should the browser client and Python game server be separate layers with an explicit protocol? | n/a | I'm not sure what the most efficient method will be and so this will be deliberated between the architect and engineer. |
| Should configuration such as player limit, tick rate, host settings, and round count be centralized? | yes | Avoid scattered tunable values. |
| Should the game render directly in browser HTML canvas rather than a native Pygame window? | yes | Matches the browser-first accessibility goal. |
| Should Pygame remain responsible for simulation and rendering exposed to the browser? | no | pygame should handle the simulation and internal game states, but the website needs to handle the rendering through javascript. |
| Should the browser receive structured game-state data and render independently in JavaScript? | yes | Avoids image transmission but requires shared visual rules. |
| Should browser input become explicit validated commands sent to the Python owner? | yes | Commands may include movement, attack, ready, and menu actions. |
| Should the Python server be authoritative for positions, collisions, scores, damage, turns, rounds, and win conditions? | yes | Clients should not submit final gameplay state. |
| Should the game use an explicit state machine for lobby, setup, turns, round results, and match results? | yes | Named states make transitions testable. |
| Should each turn have a defined action or time limit? | yes | A time limit would work best for each player. |
| Should only the host select round count and control match start? | yes | Server must validate host authority. |
| Should disconnect, reconnect, and abandoned-turn behavior be defined before multiplayer implementation? | yes | If there is a disconnect, then the game will continue on. I don't want to worry on reconnect behavior during this sprint. |
| Should every public class and function have a concise docstring? | yes | Supports the clean-code requirement. Please show me what the docstring is so I can make sure I know what that looks like on review. |
| Should the project adopt PEP 8, type hints, and descriptive naming? | yes | use pep 8 for styling guides, and use python version 3.12 for pygame |
| Should game rules and state transitions be documented near their owning code? | yes | Prevents hidden assumptions. |
| Should networking use client-server rather than peer-to-peer architecture? | yes | Supports consistent validation and state. This is my first time developing a network and client-server should be less expensive to implement. |
| Should Architect and Engineer reach unanimous consensus before selecting a networking library? | yes | Required by the project plan. |
| Should the protocol use structured messages such as JSON over WebSockets or another explicitly selected transport? | yes | Must support browser clients, four players, connection events, and ordered commands. JSON files are easier for me to read through. |
| Should the server send periodic snapshots while clients send discrete commands? | yes | Limits client authority and simplifies synchronization. |
| Should networking support four active players plus spectators or reconnection slots? | no | The connection policy must only allow for up to 4 players. |

## Engineer Questions

| [y/n] Question | Yes / no answer | Further context |
|---|---|---|
| Should each player have a fixed turn within every round? | yes | a round should allow each player a turn. This would mean up to 4 turns total depending on player count. |
| May a player move and attack during the same turn? | yes | players can move as much as they want but they have 1 attack per turn. The turn is also dependant on the timer, that is specified in the start menu. |
| Should movement be grid-based, continuous, or discrete-step? | --> | Movement should be continuous. Movement is made by going either left or right. |
| Should an attack affect only one neighboring dodgeball or every target in its hitbox? | --> | The hitbox of the dodgeball should be a slightly larger version of the circular shape of the ball. Therefore other players can potentially get hit in one attack. |
| Should knockback increase according to accumulated damage or score value? | --> | Knockback should increase based on the accumulated damage. Accumulated damage also equates to score value, but only when the end of a round occurs. |
| Should a bouncing dodgeball deduct points from every player it hits? | yes | First hit deducts 100% of the points to the ball that got hit. Second hit produces 50%, and third hit produces 25%. Any hits after the first three won't cause any more damage. When damage occurs it deducts points from the player that got hit. Players will not be able to go into the negative in terms of their points. This makes it so that if a player gets hit multiple times there is a hard cap to how many points they can lose. |
| Should players remain inside the stage by bouncing off boundaries? | yes | This is the primary difference between the way this works, and something like super smash bros. The idea is to chaotically display a ball bouncing around a box. |
| Should turns have a time limit? | yes | The time limit can be determined before the game starts in a menu type page. We should have some presets however for time limits. Presets will include: 30 seconds, 45 seconds, 1 minutes, 2 minutes. |
| Should a round end after every player completes exactly one turn? | yes | with the time limit constraints, inactive players will simply be passed over if they don't make any moves. |
| Should the server/host be authoritative for all game state? | yes | It validates inputs and resolves collisions and scores. |
| Should clients send intents rather than positions or score changes? | yes | Reduces cheating and supports deterministic simulation. Players will input movement and an attack action. The game server will then translate that on the inside in order to update positions and score changes. |
| Should the first playable milestone be single-process/local multiplayer before networking? | yes | Provides a stable baseline for synchronization. Local networking would be a substantial milestone before our true online game. |
| Should the host choose round count before match start with no mid-match changes? | yes | No further context needed |
| Should the match stop after the final round and display the winner? | yes | No further context needed |
| Should development pause at each approved stopping point for manual user testing? | yes | Engineer stops and waits for explicit approval. Before developing the game you need to write a proposal for the user to approve. Then develop under the guidelines of that proposal. |
| Should user approval be required before changing an approved stopping point or scope? | yes | Record changed acceptance criteria before resuming. Human input is critical for this project to work properly. |

## QA Questions

| [y/n] Question | Yes / no answer | Further context |
|---|---|---|
| Must the game support current Chrome, Edge, Firefox, and Safari? | no | For our first version we will develop, solely, for Chrome. |
| Must desktop and mobile/tablet form factors be supported? | no | We will only focus on desktop for our first version. Further accessibility beyond that, will be handled in later version. |
| Must four players connect over a public or LAN network? | --> | For the LAN milestone we will need to obviously need LAN support, but the full version of the game will support online play. |
| Must the frontend provide a polished shell beyond a canvas/debug view? | yes |  Lobby Screen: allows players to create a server via a code, that code can then be sent to their friends in order to join. We will not worry about public lobbies. Gameplay HUD: The HUD should be similar to super smash bros. A colored line will represent the player matching that color, and below that short line, there should be a number representative of their damage. A timer should be counting down in the center top of the game screen, for the player's time limit, and in the top left a counter should display what round number they are on. The game over screen should be kept simple and should display the name of the winner's color.  |
| Must the canvas resize responsively without changing gameplay coordinates? | yes | If the canvas needs to resize at all, which it shouldn't for this first version, then there should be no affect made on the game window. |
| Must all core actions be usable without a mouse? | yes | Movement should be handled with either A or D(for WASD movement) or the arrow keys. The attack button should be handled with the E key. |
| Must the frontend meet a target such as WCAG 2.2 AA? | no | For our first version, we will not worry about these guidelines since we will need to do extensive manual testing on the first version. Once we are gearing up for a more official release then we will handle those guidelines. |
| Must collision outcomes be deterministic for identical inputs and initial state? | yes | We will use a deterministic approach to the physics since we are only dealing witha 2 dimensional space. This will allow for better testing as well. The tick rate we'll work with for this game will be 60 fps. |
| Must players and bouncing balls remain inside the stage at all times? | yes | when creating a stage, there must be a boxed edge that keeps all of the players enclosed. |
| Must collision tests cover grazing, overlap, high speed, simultaneous collisions, and invalid dimensions? | yes | define tests that handle these subjects. |
| Must automated tests include unit, integration/network, frontend, and end-to-end smoke coverage? | --> | for this first version we will simply want to handle unit testing. Later versions will focus on end-to-end and smoke testing. |
| Must tests run on every pull request and default branch in CI? | no | if tests run properly then that won't need to run at all times, or even when we're just doing a pull request. |
| Must CI fail on lint, type-check, test, accessibility, or performance regressions? | no | We will be developing solely on this machine so we won't need to worry about lint checks for this project. |
| Must QA verify four concurrent players before release? | yes | QA should verify errors when the host disconnects (which should end the game). They should also try running a test case with four players connect. If that is not possible without four different machines then this can be dropped. This is not an issue that determines the success of the sprint. |
| Must release satisfy a written acceptance checklist approved by the user? | yes | Much like the engineer, write a proprosal for the testing checklist for the user to verify before development. |

## Pre-development dependencies

- The user answers the questions above.
- Architect and Engineer agree on networking library and protocol, then obtain user approval before networking implementation.
- Architect publishes structure, coordinate system, canvas scaling, and hitbox ownership.
- Engineer defines simulation tick, movement/collision ordering, scoring, and invalid-input behavior.
- QA identifies test runners, dependency installation, and CI provider.
