# Domino Cost App

This describes the how to setup and run `Domino Cost App`.

_Table of Contents_

- [Create New Project (optional)](#create-new-project-optional)
- [Publish the App ](#publish-the-app)
  - [Checking running status](#checking-running-status-optional)
- [Accessing Domino Cost App](#accessing-domino-cost-app)

# Create New Project (optional)

To deploy Domino Cost app we need a project to be a home for it. We recomend creating a specific project for it.

1. Go to the project's dashboard and click on `New Project`

   ![project's dashboard](/img/01.projectsDashboard.png)

2. Select a name and visibility that you prefer for this project.

   ![create new project](/img/02.createNewProject.png)

---
# Publish the App 
Now that we have a dedicated project to host our app. In order to publish it follow this steps:

1. Download the files in the [/app](/app) folder and go to the `Code` section by clicking in the side bar of the project. There, upload the three files into the project:

   ![upload files](/img/03.uploadFiles.png)

2. Verify that they are uploaded properly:

   ![files in project](/img/04.files.png)


3. Navigate to the `App` section in the sidebar of the project and select a name for the Domino Cost App that you prefer and you can easily identify. The standar environment and the smaller harware tier will be enought to run it.

   ![project's dashboard](/img/05.publishApp.png)

4. After publishing it, we'll be redirected to the `App Status` pages. 

   ![project's dashboard](/img/06.runApp.png)
   
   We'll have to wait until the status changes to `running`.

   ![project's dashboard](/img/07.appStatus.png)

   In this moment all the requeriments for the Domino Cost App to run will start to be installed and it will take a moment until the app is actually running.

## Checking running status (optional)
  If we want to verify the proper set up of our up will be able to do that from the app's user output. To be able to access them, just follow the next steps:
  1. Click on `App versions` tab.

   ![appVersions](/img/08.appVersions.png)

  2. Click on the las newest version in the table and a side bar will be display in the right of the screen.

   ![logs](/img/09.logs.png)
  
  3. Click on `User Output` and you'll see a log showing the setup of the environment. Once the legend `Solara server is starting at http://0.0.0.0:8888`, your app is ready.

   ![logs](/img/10.serverRunning.png)

---

# Accessing Domino Cost App

After a moment that the status app is status is set as `running` you'll be able to access the app by clicking in the button `View App` in the UI.

   ![project's dashboard](/img/07.appStatus.png)

You'll see a loading screen for a moment 

   ![project's dashboard](/img/11.loadingScreen.png)

And then Domino Cost app dashboard will be displayed

   ![project's dashboard](/img/12.dahsboard.png)