# Domino Cost App

This describes the how to setup and run `Domino Cost A`.

- For more on the Cucu framework see `cerebrotech/cucu` repo.
- If you have any questions please slack `#qe-automation`, thanks!
- All commands assume you are in the `e2e-tests/` directory unless otherwise noted.

_Table of Contents_


- [End-to-End Tests](#end-to-end-tests)
- [Installation - Dev-v2](#installation---dev-v2)
  - [Secret Management](#secret-management)
  - [All Users: Setup Read Access](#all-users-setup-read-access)
  - [Admin Runbook: Setting up Read Access for a New User](#admin-runbook-setting-up-read-access-for-a-new-user)
  - [Troubleshooting](#troubleshooting)
    - [Python 3.9.7 on MacOS Monterey](#python-397-on-macos-monterey)
- [Develop Tests Walkthrough](#develop-tests-walkthrough)
  - [Running Tests](#running-tests)
  - [Writing Tests](#writing-tests)
  - [Debugging Tests](#debugging-tests)
- [Tagging Tests](#tagging-tests)
  - [Testing Requirements](#testing-requirements)
- [Using Variables](#using-variables)
- [Custom Steps](#custom-steps)
  - [API Steps](#api-steps)
  - [UI Steps](#ui-steps)
  - [Kubernetes Steps](#kubernetes-steps)
  - [Implementing a Custom Step](#implementing-a-custom-step)
  - [Templatized Steps](#templatized-steps)
- [Adding New Secrets to Tests](#adding-new-secrets-to-tests)
  - [How things work in CI](#how-things-work-in-ci)
- [Standard Guidelines for Tests](#standard-guidelines-for-tests)
  - [Scenarios must be _Idempotent_](#scenarios-must-be-idempotent)
  - [Custom steps should _ALWAYS_ be generalized](#custom-steps-should-always-be-generalized)
  - [Handling non-standard HTML Components](#handling-non-standard-html-components)

# Installation - Dev-v2

This works on dev-v2, but also should work on local Mac setup.

1. Open the `e2e-tests` directory in a terminal
   ```bash
   cd $DOMINO/e2e-tests
   ```
2. Verify the version of python is in `3.9` to `3.11`, e2e-test currently supports these versions.
   ```
   python -V
   ```
3. Install cucu

   ```bash
   pip install -r requirements.txt
   ```

   In general, this is a good idea especially when switching between or syncing branches.

4. Run the script to generate [e2e-tests/cucurc.yml](cucurc.yml)

   ```
   bin/init_setup.sh https://foobar1234.quality-team-sandbox.domino.tech [ADMIN_USERNAME] [ADMIN_PASSWORD]
   ```

   🟡 Replace **foobar1234.quality-team-sandbox**, **[ADMIN_USERNAME]**, and **[ADMIN_PASSWORD]** with correct values.

5. Enable the monitor image (optional)

   ```
   echo "CUCU_MONITOR_PNG: .monitor.png" >> ~/.cucurc.yml
   ```

   With this setting, you can open `.monitor.png` during the test. This image will update automatically as the test progresses.

6. Export any additional env vars used by the tests you want to run (optional)
   ```
   export DOMINO_COMPUTE_NAMESPACE=$(kubectl get ns -l domino-compute=true -o json | jq -r '.items[0].metadata.name')
   ```

---

**Note:**

You may want to increase the memory request for the small hardware tier on your dev-v2 deployment. Whereas a normal deployment is
auomatically configured to have a small hwt with a 4GiB memory request and memory limit, dev-v2 deployments only have a .25GiB memory
request. Some tests, specifically those that spin up compute clusters, will fail with this very low memory request.

---

## Secret Management

We use `AWS Secrets Manager` to manage secrets. Here's how to setup your development machine.
(_Note_: It is the same mechanism used in system tests and you only need to set it up once for both test suites.)

## All Users: Setup Read Access

1. Request a `quality-team-sandbox` IAM user in #qe-automation Slack. Tag Brian Colby, who is a `qualty-team-sandbox` admin.
1. If Brian is not available or you're not getting attention, tag Michael Brown.
1. A `quality-team-sandbox` admin will DM you a privatebin link with your credentials.
1. Your credentials must be put into `~/.aws/credentials`, including the `[e2e-test]` line for profile recognition:
   ```ini
   [e2e-test]
   aws_access_key_id = [REDACTED]
   aws_secret_access_key = [REDACTED]
   ```
   Don't overwrite other contents! It's fine to append these three lines.
1. Test that you are able to resolve secrets by running
   ```bash
   aws --region us-west-1 --profile e2e-test secretsmanager get-secret-value --secret-id E2E_SECRETS
   ```
   which should produce output that includes textual rendering of a secrets dictionary.

## Admin Runbook: Setting up Read Access for a New User

1. Open Okta and launch the AWS application or use https://dominodatalab.okta.com/app/UserHome?fromLogin=true
1. Once you follow the link, pick the account `quality-team-sandbox`
1. Go to the `Services -> Security, Identity, & Compliance -> IAM`
1. Check to make sure the user isn't already present; sometimes they forget.
1. Otherwise, click `Users` -> `Add Users`
1. Pick a username that matches the user's `first.last`.
1. Click `Next` and `Attach Policies Directly`
1. Search for `E2ETestsSecretsManagerRead` and check it on the left side
1. Click `Next`.
1. Ensure the user is created with the tag key `user_email` and the tag value of the user's Domino email.
1. Complete the wizard to create the user
1. When the user is created, find and click the new user's name; click `Security Credentials`.
1. Click `Create Access Key`; choose Other and click Next. Click `Create access key`
1. Click `Show` by `Secret access key`.
1. Prepare a [PrivateBin](https://privatebin.domino.tech/) with contents thusly and DM to the requesting user:
   ```ini
   [e2e-test]
   aws_access_key_id = [REDACTED]
   aws_secret_access_key = [REDACTED]
   ```

## Troubleshooting

### Python 3.9.7 on MacOS Monterey

MacOS Monterey upgrade - Install python 3.9.7 if it is missing

```
pyenv install --patch 3.9.7 < <(curl -sSL https://github.com/python/cpython/commit/720bb456dc711b0776bae837d1f9a0b10c28ddf2.patch\?full_index\=1)
```

# Develop Tests Walkthrough

This is a quick intro to e2e-tests, after which we recommend to:

- Read other some tests in [e2e-tests/features/domino/](features/domino/)
- Search for different steps
  ```bash
  cucu steps | fzf
  ```
  (`brew install fzf` first)
- Ask questions from your Pod QE
- Slack #qe-automation

## Running Tests

Running your first test

1. Run the test
   ```
   cucu run features/domino/projects/orient_yourself.feature
   ```
  - You won't see a browser since it runs `--headless` by default.
    - On local mac just add the `--no-headless` arg to watch it take over your browser
    - On dev-v2 there are different options to watch it in the browser (see #qe-automation)
2. You should see the console output similar to this

   ```gherkin
   @docs/bc1c6d/step-0--orient-yourself-to-domino
   Feature: Orient yourself

     Scenario: User will find various elements on screen after logging in
       Given I open a browser at the url "{BASEURL}"                                      #  in 5.963s
       # BASEURL="https://rodney12433.quality-team..."
         And I login with username "{ADMIN_USERNAME}" and password "{ADMIN_PASSWORD}"
         ⤷ When I wait to write "integration-test" into the input "Username"              #  in 0.126s
         ⤷  And I wait to write "************************" into the input "Password"      #  in 0.051s
         ⤷  And I click the button "Login"                                                #  in 3.516s
         ⤷ Then I wait up to "120" seconds to see the text "Projects"                     #  in 0.302s
         And I login with username "{ADMIN_USERNAME}" and password "{ADMIN_PASSWORD}"     #  in 6.068s
         # ADMIN_USERNAME="integration-test" ADMIN_PASSWORD="************************"
        Then I should see the button "Lab"                                                #  in 0.705s
        ... truncated ...
   ```

3. [Optional] Generate a html report by either
  - Adding the `--generate-report` arg
  - Or running the command
   ```bash
   cucu report
   ```
   And it will save to `the [e2e-tests/report/](report/) directory

## Writing Tests

1. Navigate to [e2e-tests/features/domino/](features/domino/)
2. For your feature navigate to the corresponding sub-folder, or create a new folder if needed
3. Create a `.feature` file. The name should be short.
4. Copy the contents below into your file

   ```gherkin
    @docs/
    Feature: My new feature
      Some description here

      Background: For every scenario run create these unique values
        Given I set the variable "USER_NAME_ADMIN" to "admin-{SCENARIO_RUN_ID}"  # omit if you don't need an admin account
          And I create a user with roles "SysAdmin,Practitioner", email "{USER_NAME_ADMIN}@testing.jobs", username "{USER_NAME_ADMIN}", password "{SCENARIO_RUN_PWD}", firstname "{USER_NAME_ADMIN}" and lastname "{SCNEARIO_RUN_ID}" via keycloak API
          And I login the user with username "{USER_NAME_ADMIN}" via keycloak API
          And I set the variable "USER_NAME" to "pract-{SCENARIO_RUN_ID}"
          And I set the variable "PROJECT_NAME" to "proj-{SCENARIO_RUN_ID}"

      @testrail()  # need to fill this out
      Scenario: This is my user story
        Given I create a user with roles "Practitioner", email "{USER_NAME}@testing.jobs", username "{USER_NAME}", password "{SCENARIO_RUN_PWD}", firstname "Pract" and lastname "{SCENARIO_RUN_ID}" via keycloak API
          And I create a temporary private project "{PROJECT_NAME}" with username "{USER_NAME}", password "{SCENARIO_RUN_PWD}" via domino API
          And I open a browser at the url "{BASEURL}"
          And I login with username "{USER_NAME}" and password "{SCENARIO_RUN_PWD}"
         When I navigate to the url "{BASEURL}/u/{USER_NAME}/{PROJECT_NAME}"
         Then I wait to see the project title is "{PROJECT_NAME}"
   ```

5. Fill out the `@docs/` and `@testrail()` tags
  - For values see your requirements doc, PM, QE, etc
  - More info on tags below
6. Save and run it!

## Debugging Tests

Now on to debugging!

- Running a test will create a `results` directory with the following:
  - _results/[feature name]/[scenario name]/\*.png_
    - a screenshot taken after each step has executed.
  - _results/[feature name]/[scenario name]/logs/browser_console.log_
    - the browser console log for that scenario
  - _results/TEST-[path to feauture file][feature name].xml_     
    - the Junit XML report for that feature
  - _results/run.json_
    - a JSON object containing details for each step, including state (pass,
      fail, skip), scenario and feature, and duration.
- But you may want to read the HTML report instead.
  ```bash
  cucu run report
  ```
  Will create the `report` directory
- Add the `--ipdb-on-failure` to the `cucu run` to drop into a [ipython](https://ipython.readthedocs.io/en/stable/) debugger on failure

# Tagging Tests

1. Tags are very important as they provide:

  - Critical metadata for reporting and tracking
  - Control where it runs in CI
  - Declare Domino features used (ex. `@liteuser`, `@workspaces`)
  - Filtering on what tests should run

2. They can be at the **Feature** file level or at the **Scenario** level.

3. Here's a list of some notable tags
   | Tag | Gist | Example |
   | ---------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------- |
   | @testrail(####) | **[Required]** The TestRail TestCaseID (numbers only) that is linked to TestRail in reporting (should be 1-1 mapping) | @testrail(86287) |
   | @doc/[TestableRequirementID]/[OptionalSubPath] | **[Required]** The permalink that is linked to the docs site in reporting - see [testing requirements](#testing-requirements) | @docs/bc1c6d/step-0--orient-yourself-to-domino |
   | @[Domino Feature] | **[Encouraged]** Each test should be tagged with the major features it uses | @liteuser @workspace |
   | @nexus-only | Add this to a test that will only work in a nexus deployment with a remote data plane **Mutually exclusive** with @no-nexus | @nexus-only |
   | @no-nexus | Add this to a test that will not work in a nexus deployment **Mutually exclusive** with @nexus-only | @no-nexus |
   | @cloud-only | Add this to a test that will only work in a cloud deployment **Mutually exclusive** with @no-cloud | @cloud-only |
   | @no-cloud | Add this to a test that will not work in a cloud deployment **Mutually exclusive** with @cloud-only | @no-cloud |
   | @toast | Add this to auto-close toast dialogs, but you **cannot use any toast messages** (either dialog or popup) in your test. | @toast |
   | @disabled | **[Discouraged]** A test that was working but needs to be skipped for a sprint (should also have a JIRA tag) | @disabled @DOM-39936 |
   | @workaround | A test that has a workaround for a product bug (should also have a JIRA tag) | @workaround @DOM-36641 |
   | @[JIRA-ID] | JIRA ticket of work todo | @PLAT-5636 |
   | #@implement-me | Use on a **commented out** test prototype or draft (tag is also commented out) | #@implement-me |
   | @skip-vcluster | **[Discouraged]** Don't run on vcluster because of vcluster limitations (should also have a JIRA tag) | @skip-vcluster @PLAT-5141 |

## Testing Requirements

You may have noticed the tag `@docs/...`, which is used for our initiative to
track coverage of [Testing Requirements](https://dominodatalab.atlassian.net/wiki/spaces/ENG/pages/1332085021/Tracking+Requirements+Coverage).

The format for these tags is:

```
@docs/perma-link/optional-path/#anchor-from-doc
```

Where:

- `perma-link` is a 6 digit hex code in the URL link of the documentation page.
- `optional-path` is an optional path. It has no real effect, since the `perma-link` dictates the exact page to load, but it can be used for readability.
- `#anchor-from-doc` is an existing section header (which is preferred) or a `[[TR*]]` you created in the docs repo that links to a more specific part of the page.

From the tag, its quite straightforward to construct a URL to get back to the docs page:

- https://devdominodocs.gatsbyjs.io/en/latest/bc1c6d/step-0--orient-yourself-to-domino

# Using Variables

Variables are values that are accessible with the `{}` syntax inside `""` quotes.

Feel free to store your variable values in:

1. For per-scenario values use the `I set the variable...` steps
2. For non-secreet constants use `e2e-tests/features/domino/cucurc.yml`
3. For secrets use the AWS Secrets Manager - see [Adding New Secrets to Tests](#adding-new-secrets-to-tests)

Try to set variables in a `Background:` at the beginning of your Feature file for easy access
in all your scenarios. Don't worry, each scenario will get their own unique value
provided by `{SCENARIO_RUN_ID}` and for passwords use `{SCENARIO_RUN_PWD}`.

```gherkin
  Background: For every scenario run create these unique values
    Given I set the variable "USER_NAME" to "manajobs-{SCENARIO_RUN_ID}"
      And I set the variable "PROJECT_NAME" to "Manajob-{SCENARIO_RUN_ID}"
```

# Custom Steps

## API Steps

[cucu custom API steps](features/steps/api/)

In some cases, you want to do some action that isn't part of the feature
being validated, but is more of a test fixture (such as create a user or
project, launch a workspace, etc.). In these cases, you should use an API
step that can get that done reliably and efficiently. You can see an example
[here](features/domino/projects/create_project.feature)

You can see the scenarios on that file all begin with a step that
ends with `via keycloak API`. This step ending tells the reader that
the step is using the API to create a user. All API steps should follow
this pattern, and end the step name with `via ... API` to make it
obvious that the step does not do anything in the UI, even if there is a browser
open at that point in the test execution.

## UI Steps

[cucu custom UI steps](features/steps/ui/)

Unlike templatized steps, custom steps are domino-specific UI steps that use
the browser directly to find elements and interact with them. These are different
than cucu's built-in steps an that the components they interact with are not standard,
and do not adhere to any standards such as [ARIA](https://www.w3.org/TR/wai-aria-1.1/).
This means that all custom steps should be Domino-specific.

We want to try to avoid creating custom steps as much as possible.
Even implementing as many steps as possible as API steps, we need
custom UI steps in order to implement some tests. When you encounter
such a need, open a ticket in the DOM project to rework the DOM so that
cucu's built-in steps can be used, and then open a ticket in the QE project
to refactor the test to remove the relevant custom step.

## Kubernetes Steps

[cucu custom Kubernetes steps](features/steps/kubernetes/)

Cucu tests simulate a user interacting with Domino via the UI. So, for the vast majority of
cucu tests, you should not access the underlying Kubernetes infrastructure (e.g. via `kubectl` or
HTTP requests to the Kubernetes API server).

That said, there are some cases where the best way to test UI functionality is to modify Kubernetes resources
and then check what happens in the UI. For example, there are failure modes that are very difficult or impossible
to trigger via the UI or Domino API ("If Kubernetes resource X is suddenly deleted, then the UI should change in
so-and-so way"). If the best way you can think of to trigger the scenario you want to test is by interacting with
Kubernetes directly, then you can implement a custom Kubernetes step.

Custom Kubernetes steps:

1. _Should_ issue `kubectl` commands using Python's `subprocess` module.
2. _Should not_ have `@step` text that implies the user knows about or issues the `kubectl` command. Instead, the
   `@step` text should convey that the step happens without the user's knowledge or agency.
   An example: `@step('some unexpected error kills the "{cluster_type}" in the project "{project_name}"')`.

## Implementing a Custom Step

The first step (lol) for implementing a custom step is to decide if you will
be implementing the functionality through an API interaction or a UI interaction.
Based on that decision you will be adding to either the [ui](features/steps/ui/)
or [api](features/steps/api/) directories.

Next, you will have to decide if your new step fits into one of the existing modules.
Don't be afraid to add a new module if you are implementing a step in a new area.
It is important, though, that we keep the modules clearly named and that they
follow the naming pattern `*_steps.py`.

_If you do end up adding a new module_, it is important that you wire up the module
so that cucu can find it. To do so, add an import statement to
[features/steps/**init**.py](features/steps/__init__.py).

After adding your custom step definition, an easy way to make sure everything is
hooked up properly is to run `cucu steps` and `grep` for your step.

## Templatized Steps

As you look at test output, you may notice those steps indented and
prefixed with `⤷`. These steps are called "templatized steps," and they
group together a series of other steps. This allows complex actions to be
encapsulated into a single step, so that large blocks of steps can be
reproduced without the need to copy/paste the entire block.

The step implementation is quite simple and looks like so:

```python
  @step('I login with username "{username}" and password "{password}"')                                                                                                                                                def login_with_username_password(ctx, username, password):                                                                                                                                                               run_steps(                                                                                                                                                                                                               ctx,                                                                                                                                                                                                                 f"""
           When I wait to write "{username}" into the input "Username"
            And I wait to write "{password}" into the input "Password"
            And I click the button "Login"
           Then I wait up to "{{LOGIN_TIMEOUT_S}}" seconds to see I am logged in
           """,
      )
```

The step takes in a `username` and `password` and then does the necessary UI
interactions and also verifies the user is logged in. Templatized steps are only
intended for things that you can _NOT_ do through the _API_ and for groups of
steps that are reused across many tests.

# Adding New Secrets to Tests

**Tag Brian Colby in Slack in #qe-automation that you need to add/modify/remove an E2E_SECRET in AWS Secrets manager. Depending on the nature of the configuration you may be asked to add some documentation about your secret on confluence.**

You will need to provide a link to a (PrivateBin)[https://privatebin.domino.tech/] containing the new/updated Key Value pairs, or just a list of the Keys to remove.

After following the previous section and having your credentials in place you
can now go back to the `Secrets Manager` and you should see a secret listed
with the name `E2E_SECRETS`. This is the secret that cucu uses. Any additional
secrets _MUST_ all start with the prefix `E2E_SECRET_`, as that is the only way
the framework can make out that this variable value is pulled from the
`Secrets Manager`. Once added, you can run your test with the same
`E2E_SECRET_XXX` reference, and it will simply attempt to pull your secret
value from AWS.

1. Click the `E2E_SECRETS` link
2. Click the `Retrieve Secret Value` button
3. Click `Edit` and add in a new row with your secret

## How things work in CI

In CI we set the variables:

- `E2E_TEST_AWS_ACCESS_KEY_ID`
- `E2E_TEST_AWS_SECRET_ACCESS_KEY`

And those are from the user `e2e-test` in AWS IAM which has the required access
to the `Secrets Manager` as any regular user would.

# Standard Guidelines for Tests

In this section, we'll describe various principles and guidelines that can
make writing end to end scenarios easier to maintain in the long run, as well as
more reliable when running in CI.

## Scenarios must be _Idempotent_

This means a scenario can be rerun as many times as you'd like from any starting
state (ie from having previously aborted a test run of the same scenario
or another) and never fail because of existing state.

This can be quite hard to do in some cases, but so long as your scenario does the
following few things, then idempotency should be possible:

1. Delete fixtures that may have been left behind from a previous
   failed run. This includes fixtures that aren't "temporary," and
   therefore already cleaned up by exit hooks, as in the `create a temporary project` steps in [here](features/steps/api/project_steps.py)
2. Always use API steps to create new fixtures. When possible, create steps
   that use the notion of "temporary" fixtures and clean them up with
   exit hooks.
3. Use unique names for fixtures. You can achieve this using the variable
   `{SCENARIO_RUN_ID}`, which generates a unique id every execution of
   your scenario. This helps prevent collisions when running scenarios
   (even in the same feature file) in parallel with one another.
4. Never make a scenario dependent on another. The run order of
   scenarios in a feature file is not guaranteed, and dependencies break
   idempotency.
5. Scenarios in the same feature file may not necessarily be run using the
   same test executor (ie cucu process). To enforce test correctness when
   running different scenarios in different test executors, cucu resets all variables
   between scenarios. This means that tracking state in memory or even
   trying to share variable across different scenarios will never work.

## Custom steps should _ALWAYS_ be generalized

When you write a new custom step, you shouldn't hide anything in the step that
could be used by others that want to use the same step for other applications.
An example of this is that if you write a step that reads/writes from a location
on the file system _never_ impose a hard coded internal location you read/write
those files from but instead allow the test writer to read/write from any
location by either assuming you're in the `e2e-tests` directory (recommended
way) and so all paths are relative to the `e2e-tests` directory or they can
reference an absolute path outside of the `e2e-tests` directory but this should
_ONLY_ be done for very specific reasons as this can make tests less portable.

## Handling non-standard HTML Components

Sometimes, you may run into UI elements styled to look like buttons, but that
can't be found by `I should see the button` steps or `I click the button` steps.
This is likely because the button was a special `<div>` element
without the required ARIA attributes to make the testing framework
see it as a button. In order for us to move forward in testing and make our
product more accessible, we are currently handling this situation by filing a
bug on the "inaccessible" element under:

- https://dominodatalab.atlassian.net/browse/DOM-39341

The scenario can still be written by creating a custom step with
custom logic to interact with the element in question.
For example, see the stop/archive/compare buttons on the jobs
pages [here](features/steps/ui/jobs_steps.py).
