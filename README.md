[![New Relic Experimental header](https://github.com/newrelic/opensource-website/raw/master/src/images/categories/Experimental.png)](https://opensource.newrelic.com/oss-category/#new-relic-experimental)

# Synthetics Sync
Github action that will sync synthetic script commits to corresponding Synthetic monitors within New Relic.

Currently supports the following for Scripted Browser or Scripted API type monitors:
 - Syncing script changes to existing monitors.
 - Creating new monitors for new scripts committed.
 - Deleting monitors when associated scripts are deleted.

## Requirements
1. Configure your [New Relic User key](https://docs.newrelic.com/docs/apis/intro-apis/new-relic-api-keys/#user-key) as a repository secret.
2. Create and configure your Workflow yaml ([see examples here](#examples)) under `.github/workflows`.

**IMPORTANT**
* This action depends on the use of [tj-actions/changed-files](https://github.com/tj-actions/changed-files) to detect changes to any js files committed or removed.
* Filenames of scripts committed should be 1-1 exact with the corresponding `monitorName` within New Relic.
* If you plan on creating **new monitors** from newly committed scripts, each script must have one of the following comments somewhere within, to denote the monitor type (scripted browser or scripted api):

```js
//monitorType: SCRIPT_BROWSER
```
OR
```js
//monitorType: SCRIPT_API
```

## Usage

```yaml
name: New Relic Synthetics

# -------------------------------------------------------------------------------------------------------------------------
# Event `push`: Compare the preceding commit -> to the current commit.
# -------------------------------------------------------------------------------------------------------------------------
on: [push]

env:
  NEW_RELIC_API_KEY: ${{ secrets.NEW_RELIC_API_KEY }} #Required repository secret

jobs:
  sync_synthetic_monitors:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v3


      # Detects changes to .js files only in any sub path, formats those filenames/paths as json
      - name: Get Changed Scripts
        id: changed-files
        uses: tj-actions/changed-files@v35
        with:
          separator: ","
          files: |    # Modify this to wherever your specific scripts reside - defaults to any js files
            **/*.js
          json: "true"

      # Proceed with storing filenames/paths in a local file for further processing, ONLY if any .js files have been modified
      - name: Store Changed Scripts
        if: steps.changed-files.outputs.any_changed == 'true'
        run: |
          echo ${{ steps.changed-files.outputs.all_changed_files }} > changed_monitors.json
          cat monitors.json

      - name: Store Deleted Scripts
        if: steps.changed-files.outputs.any_deleted == 'true'
        run: |
          echo ${{ steps.changed-files.outputs.deleted_files }} > deleted_monitors.json
          cat deleted_monitors.json

      # Parse out js filenames, which should match the entity names within NR, fetch the entity's guid, and update existing monitor or create new one
      - name: Sync Changes to Synthetics
        if: steps.changed-files.outputs.any_changed == 'true'
        uses: newrelic-experimental/synthetics-sync@v1.3
        with: # OPTIONAL defaults for creation of new scripts committed
          accountId: ""
          privateLocations: ""
          publicLocations: ""
          interval: ""
          status: ""
```

## Inputs
The following are optional inputs if you wish to automatically **create** new monitors from newly committed scripts. If these are not included in the workflow, only changes to existing scripts will be synced with New Relic.

| INPUT            | TYPE   | REQUIRED | DEFAULT | DESCRIPTION                                                                                                                                                                                                                                                                                |
| ---------------- | ------ | -------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| accountId        | string | FALSE    | ""      | New Relic account id in which new monitor will be created within                                                                                                                                                                                      
| privateLocations | string | FALSE    | ""      | Array of private location guids that the new monitor will execute on. guids can be found within New Relic under Synthetic Monitoring -> Private Locations                                                                                                                                  |
| publicLocations  | string | FALSE    | ""      | Array of public location names that the new monitor will execute on. The AWS region must be used, not the display name. A list of location inputs can be found [here](https://docs.newrelic.com/docs/synthetics/synthetic-monitoring/administration/synthetic-public-minion-ips/#location) |
| interval         | string | FALSE    | ""      | The execution frequency of monitor created. Available options can be found [here](https://docs.newrelic.com/docs/apis/nerdgraph/examples/nerdgraph-synthetics-tutorial/#period-attribute)                                                                                                  |
| status           | string | FALSE    | ""      | Whether a new monitor created within New Relic will be enabled or disabled. Accepts `ENABLED`, `DISABLED`, or `MUTED`                                                                                                                                                                     |


## Examples
Below are a couple different configurations for various use cases:

<details>
<summary>Sync modified scripts only</summary>

```yaml
...
  - name: Sync Changes to Synthetics
    if: steps.changed-files.outputs.any_changed == 'true'
    uses: newrelic-experimental/synthetics-sync@v1.2
    with:
      accountId: ""
      privateLocations: ""
      publicLocations: ""
      interval: ""
      status: ""
...
```
</details>

<details>
<summary>Sync modified scripts with existing monitors and create new monitors with default inputs - 2 private locations and 2 public locations, running on the new runtime every 30 minutes</summary>

```yaml
...
  - name: Sync Changes to Synthetics
    if: steps.changed-files.outputs.any_changed == 'true'
    uses: newrelic-experimental/synthetics-sync@v1.2
    with: # all optional defaults for creation of new scripts committed
      accountId: 123
      privateLocations: "[{'guid': 'xtz'},{'guid': 'abc'}]"
      publicLocations: "['AWS_AP_EAST_1', 'AWS_US_EAST_2']"
      interval: EVERY_30_MINUTES
      status: ENABLED
...
```
See [inputs](#inputs) for more information.
</details>

## Additional Resources
* [Managing Synthetic Monitors w/ GraphQL](https://docs.newrelic.com/docs/apis/nerdgraph/examples/nerdgraph-synthetics-tutorial/)
* [Public Locations](https://docs.newrelic.com/docs/synthetics/synthetic-monitoring/administration/synthetic-public-minion-ips/#location)
* [Intro to Writing Scripts](https://docs.newrelic.com/docs/synthetics/synthetic-monitoring/scripting-monitors/introduction-scripted-browser-monitors/)

Check out example [repo here](https://github.com/khpeet/local-newrelic-synthetics-example/actions) that uses this action.

## Contributing

We encourage your contributions to improve [Synthetics Sync](../../)! Keep in mind when you submit your pull request, you'll need to sign the CLA via the click-through using CLA-Assistant. You only have to sign the CLA one time per project. If you have any questions, or to execute our corporate CLA, required if your contribution is on behalf of a company, please drop us an email at opensource@newrelic.com.

**A note about vulnerabilities**

As noted in our [security policy](../../security/policy), New Relic is committed to the privacy and security of our customers and their data. We believe that providing coordinated disclosure by security researchers and engaging with the security community are important means to achieve our security goals.

If you believe you have found a security vulnerability in this project or any of New Relic's products or websites, we welcome and greatly appreciate you reporting it to New Relic through [HackerOne](https://hackerone.com/newrelic).

## License

Synthetics Sync is licensed under the [Apache 2.0](http://apache.org/licenses/LICENSE-2.0.txt) License.

>Synthetics Sync also use source code from third-party libraries. You can find full details on which libraries are used and the terms under which they are licensed in the third-party notices document.
