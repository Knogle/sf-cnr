<!-- PROJECT LOGO -->
<br />
<p align="center">
  <a href="https://sfcnr.com">
    <img src="https://i.imgur.com/Yzq9JiT.png" alt="Logo" width="128" height="128">
  </a>

  <h3 align="center">San Fierro Cops And Robbers</h3>

  <p align="center">
    A fun and old cops and robbers gamemode for the SA-MP multiplayer modification
    <br /><br />
    <a href="https://sfcnr.com"><strong>Play the live server svr.sfcnr.com:7777 »</strong></a>
  </p>
</p>

<!-- TABLE OF CONTENTS -->
## Table of Contents

* [About the Project](#about-the-project)
* [Credits](#credits)
* [Getting Started](#getting-started)
* [Features](#features)
* [Contributing](#contributing)
* [License](#license)
* [Contact](#contact)

<!-- ABOUT THE PROJECT -->
## About The Project

[![SF-CNR][sf-cnr]](https://sfcnr.com)

San Fierro Cops And Robbers begun in late 2012 of December as a basic incomplete cops and robbers server that took 
the SA-MP community by being unique - for example, being the first Cops And Robber server to allow Deathmatch.

For over half a decade, San Fierro Cops And Robbers has been supported by thousands of players and has established
a childhood memory for many.

### Credits

* Lorenc ([@zeelorenc](https://twitter.com/zeelorenc))
* Stev
* Damen
* ThreeKingZ

#### And another big thanks to the crowdfund patreons that made this possible!

* Stev
* Nibble
* Banging7Grams
* Kova
* Queen
* Panther

Credits are generally added to the top of source files, if you are missing, message me!

<!-- GETTING STARTED -->
## Getting Started

The Linux development setup below downloads a matching, pinned SA-MP toolchain and plugins. It runs the original **SA-MP 0.3.7 R2** server, with a separate MariaDB container.

Requirements: Linux x86-64, Python 3.11+, Podman (or Docker), and 32-bit libc/libstdc++ for the Pawn compiler. On Debian/Ubuntu: `sudo dpkg --add-architecture i386 && sudo apt-get update && sudo apt-get install libc6:i386 libstdc++6:i386`. On Fedora: `sudo dnf install glibc.i686 libstdc++.i686`.

From the repository root:

```sh
python3 tools/local.py setup
python3 tools/local.py build
python3 tools/local.py up
python3 tools/local.py smoke
```

Connect using an SA-MP 0.3.7 client to **127.0.0.1:7777**. `up` waits for MariaDB, applies the five bundled SQL migrations once, starts the server, and checks actual SA-MP UDP responses, all 14 plugins, MySQL, 210 NPCs and the startup logs. A client login and gameplay session remain separate manual checks.

```sh
python3 tools/local.py status
python3 tools/local.py down
# After editing Pawn files:
python3 tools/local.py build
python3 tools/local.py up
```

`down` retains the database volume (`sf-cnr-db-data`) and runtime files. Stop before rerunning `setup` or `build`. Existing `server.cfg` and `database.pwn` are preserved. Container names are `sf-cnr-server` and `sf-cnr-db`; the tooling refuses to alter containers owned by another workspace. Set `CONTAINER_ENGINE=docker` to select Docker explicitly.

The generated files are ignored by Git:

- `include/`, `.deps/compiler/`: compatible includes and Pawn compiler **3.10.8**, including its matching `libpawnc.so`.
- `.runtime/`: server, AMX files, plugins, GPS/height maps, NPC recordings and logs. Edit `.runtime/server.cfg` for server settings; the default listens on loopback and does not announce publicly.
- `.local/settings.json`: generated local database/RCON passwords. `.local/database.env` configures the database container, which listens on `127.0.0.1:3307`. Keep these files private and back them up with your database.
- `gamemodes/irresistible/config/database.pwn`: generated from the sample for that local database. Editing database connection settings requires rebuilding the AMX.
- `.cache/`: verified downloads, compiler logs, previous startup logs and `smoke-result.json`.

Dependencies and SHA-256 hashes are recorded in [tools/dependencies.lock.json](tools/dependencies.lock.json). This keeps **YSI 4**, **MySQL R39-6**, **Progress2 2.1.2** and **Streamer 2.9.3** together. FCNPC uses **2.0.11**, with the gamemode updated for its renamed ammo/aim arguments and damage callback order. TPoker is the plugin already shipped in this repository. Dead original downloads are sourced from the open.mp archive and other explicitly recorded mirrors. Downloads remain in the local cache; `setup` verifies every hash on every run.

The YSI backslash paths remain intact. The build uses the community compiler's documented [`-Z` compatibility mode](https://github.com/pawn-lang/compiler/wiki/Compatibility-mode), which translates Windows separators on Linux. Only the old standalone `foreach` reference was replaced by the already-installed `YSI\y_iterate` include. No YSI or MySQL compatibility stubs are used. Compiler warnings are treated as build failures.

The Debian runtime supplies 32-bit libraries and sets `MALLOC_MMAP_THRESHOLD_=0` for legacy plugin trampolines on SELinux hosts. It does not require a privileged container or changes to host SELinux policy. The obsolete executable-stack bit is cleared on the local MerRandom binary. FCNPC may print `No collision data found` for its optional ColAndreas module; this gamemode uses the supplied MapAndreas height maps and stationary FCNPCs instead.

Discord remains disabled as in upstream. Old external website/audio/help services require independent replacement if you want those integrations. The upstream `DEBUG_MODE` remains enabled, so destructive account-maintenance queries are skipped. Empty stock/economy aggregates now return zero when bootstrapping a fresh database.

References: [original setup guide](https://github.com/zekodef/sf-cnr/wiki/Server-Setup-Guide), [server.cfg](https://open.mp/docs/server/server.cfg), [SA-MP query protocol](https://open.mp/docs/tutorials/QueryMechanism), [FCNPC 2.0.11 API](https://github.com/ziggi/FCNPC/blob/v2.0.11/FCNPC.inc), [glibc allocation settings](https://sourceware.org/glibc/manual/latest/html_node/Memory-Allocation-Tunables.html).


<!-- USAGE EXAMPLES -->
## Features

### Trailer
[![trailer][trailer]](https://www.youtube.com/watch?v=ezZHpT4vgYY)

Credit: Dash

### List
There are dozens of features made available to users by the server
* Arresting as a COP (MMB to taze, cuff, arrest)
* Robbing stores and players
* Killing players
* Competitive experience/leveling algorithm
* Action packed gang wars - the most innovative
* Fight the house fire epidemic as a fireman (/fires)
* Chop wood as a lumberjack
* Kidnap players and hold them for ransom
* Blowing up the jail cells to break out criminals from prisons
* Constant hit contracts placed on players anonymously
* Steal furniture and cash them at the Pawn Shop.
* Mine ores and export them
* Create methamphetamine in RVs and export to Cluckin' Bell
* Bank, drug house and ship hiests
* Rob NPC security trucks (just like GTA 5).
* Blowing up Alcatraz to release the high-risk criminals
* Jacking cars and exporting them in Shipyard containers.
* Rob atms around the server
* Gamble the finest and most addicting casinos in SA-MP
* Buy and sell /stocks ... we have a P2P tradable market with stocks that can be manipulated
* Race players using our fun outrun race feature (/race)
* Buy fireworks at a local 24/7 or Supa Save to celebrate an occasion
* Play 8-Ball Pool at any bar in San Andreas
* Play Poker (up to 6 players) at any casino in Las Venturas
* House, vehicle, garage, gate, gang facility, business systems available
* Boost The Trucking Company's stock price by Trucking
* Toy/clothes system (/toys)
* Paintball system to have endless training on DM
* Passive mode system to have an uninterrupted roleplay experience (auto enabled)
* Battle Royale Minigame

Mostly all of these features have been converted into modules that can be easily utilized not only by SF-CNR developers.

<!-- CONTRIBUTING -->
## Contributing

Contributions are what make the open source community such an amazing place to be learn, inspire, and create. 

Any contributions you make are **greatly appreciated**.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

<!-- LICENSE -->
## License

Distributed under the MIT License. See `LICENSE` for more information.

<!-- CONTACT -->
## Contact

Lorenc - [@zeelorenc](https://twitter.com/zeelorenc) - zeelorenc@hotmail.com

Project Link: [https://github.com/zeelorenc/sf-cnr](https://github.com/zeelorenc/sf-cnr)

[sf-cnr]: https://i.imgur.com/IuzVeBc.png
[trailer]: http://i3.ytimg.com/vi/ezZHpT4vgYY/hqdefault.jpg
