# IMPORTANT

This repository has now been archived. No further work will be merged here.

New changes will be available in the new [costs-dashboard repository for 5.10]([https://github.com/dominodatalab/costs-dashboard](https://github.com/dominodatalab/costs-dashboard/tree/release-5.10.0))

# Domino Cost App

This repo describes how to setup and run the `Domino Cost App` along with a Domino Cost App that can be used as a starting point.

_Table of Contents_

- [Create New Project (optional)](#create-new-project-optional)
- [Publish the App ](#publish-the-app)
  - [Checking running status](#checking-running-status-optional)
- [Accessing Domino Cost App](#accessing-domino-cost-app)

# Create New Project (optional)

The Domino Cost app requires a project to be launched from.

1. Go to the project's dashboard and click on `New Project`

   ![project's dashboard](/img/01.projectsDashboard.png)

2. Select a name and visibility for this project.

   ![create new project](/img/02.createNewProject.png)

---
# Publish the App 
Once a dedicated project has been created or selected to host our app.. In order to publish it follow this steps:

1. Download the files in the [/app](/app) folder and go to the `Code` section by clicking in the side bar of the project. There, upload the three files into the project:

   ![upload files](/img/03.uploadFiles.png)

2. Verify that they are uploaded properly:

   ![files in project](/img/04.files.png)


3. Navigate to the `App` section in the sidebar of the project and add a title for the Domino Cost App that you prefer and you can easily identify. The `standard` environment and the smaller harware tier will be enought to run it.

   ![project's dashboard](/img/05.publishApp.png)

4. After publishing it, you'll be redirected to the `App Status` pages. 

   ![project's dashboard](/img/06.runApp.png)
   
   Wait until the status changes to `running`.

   ![project's dashboard](/img/07.appStatus.png)

   It will take a moment for the dependencies to install, and the Domino Cost App to start running.

## Checking running status (optional)
  To verify that the app is properly setup, you can check the app's user output. To access them, follow the next steps:
   1. Click on `View Execution Details` link.

   2. Click on `User Output` and you'll see a log showing the setup of the environment. Once the legend `Solara server is starting at http://0.0.0.0:8888`, your app is ready.
   ![logs](/img/09.logs.png)
   <br>![app running](/img/10.serverRunning.png)

---

# Accessing Domino Cost App

After a moment that the app's status will be set to running and you will be able to access the app by clicking on the button View App in the UI.

   ![project's dashboard](/img/07.appStatus.png)

You'll see a loading screen for a moment 

   ![project's dashboard](/img/11.loadingScreen.png)

And then Domino Cost app dashboard will be displayed

   ![project's dashboard](/img/12.dahsboard.png)
