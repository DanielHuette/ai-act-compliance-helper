# Reporting security vulnerabilities

**English** | [Deutsch](SECURITY.de.md)

**Context:** how to report a vulnerability and what to expect | **Input:** a vulnerability you found | **Output:** a private report, an acknowledgement and a fix where possible

## Do not report in public

**Context:** the reporting channel | **Input:** your finding | **Output:** a private message

A security vulnerability does **not** belong in a public issue.

Report it to **dhuette@gmx.net** with "Security" in the subject. If you want to encrypt, ask for
a key in a first message without details.

## What the report should contain

**Context:** the content of a report | **Input:** your finding | **Output:** a report that can be reproduced

* What the vulnerability allows.
* How to reproduce it, step by step.
* Which version is affected: tag or commit, and whether it concerns the web page, the packaged
  program, the container or the source code.
* Your assessment of who is affected.

## What you can expect

**Context:** response times of a one-person project | **Input:** your report | **Output:** what is promised and what is not

This project is run by one person alongside other work. That determines what is promised and
what is not:

* **Acknowledgement:** within 7 days.
* **First assessment:** within 30 days.
* **Fix:** no date. There is no security team and no on-call duty. Whatever is fixed is recorded
  in [CHANGELOG.md](CHANGELOG.md).
* **Credit:** if you wish, you are named in the changelog.
* **No money.** There is no bounty programme.

If nobody answers within 30 days, you may publish the vulnerability. A vulnerability that goes
unnoticed is worse than a published one.

## Supported versions

**Context:** which versions receive fixes | **Input:** none | **Output:** the supported version

Only the latest version. Older versions are not maintained.

## What counts as a vulnerability here

**Context:** the line between a vulnerability and expected behaviour | **Input:** your finding | **Output:** whether to report it here or as a normal issue

| Yes | No |
|---|---|
| A way for the user's description to leave the device unnoticed | The description goes to Claude or GPT when an application programming interface (API) key is configured. This is documented and intended. |
| A way to read a configured API key from outside | The key is read from the environment or the file `.env`; keeping that file private is up to whoever runs the service |
| Code execution through a planted file or input | The search index is stored as NumPy arrays (`.npy`) and compressed JavaScript Object Notation (JSON, `.meta.json.gz`); a modified file can cause wrong hits but cannot start code. A file in the old `pickle` format is rejected, not read |
| A dependency that brings in permissions or telemetry | A dependency with a known vulnerability but no path to exploitation here: please file a normal bug report |
| A way to let the language model replace the deterministic classification | An answer that is badly phrased |

## Not a vulnerability, but just as important

**Context:** wrong legal content | **Input:** a wrong reference | **Output:** the right route for it

**A wrong article reference.** It goes into an answer on which someone bases a decision. It
belongs in the **Legal error** template and is handled before all other reports. See
[CONTRIBUTING.md](CONTRIBUTING.md).

## What is checked and what is not

**Context:** the actual depth of security checks | **Input:** the current repository | **Output:** what you may assume and what not

So that nobody assumes more than has been checked:

* Automated tests in `tests/` check, among other things, that an injected instruction
  stays inside its section of the prompt, cannot change the classification, and that invented
  citations are reported. **No attack against a real language model** has been carried out; the
  precautions are reasoned, not tried out.
* `bandit` (static security scan) and `pip-audit` (known vulnerabilities in dependencies) run in
  the checks; Dependabot reports new versions weekly. This is checking by tools, not review by
  people.
* The **packages are not signed**. Where a package comes from can only be traced through the
  public GitHub Actions run. Signing for Windows and macOS requires a paid certificate; on macOS
  the system therefore asks for the route through the context menu on first start.

Details on where data is stored and what leaves a device:
[docs/security.md](docs/security.md).
