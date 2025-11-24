## DMIS (DENTAL MANAGEMENT INFORMATION SYSTEM)

A dentail clinical management information system for appointment scheduling and patient flow optimization

### GETTING STARTED
If you have already done all of this you can skip. To run this up for local development run the following commands on your terminal.

Clone the git repo onto your machine
```
git clone https://github.com/duckdoe/DMIS.git
```

cd/switch into the new directory
```
cd DMIS
```

Create a virtual enviroment
```
python -m venv venv
```

**This alternative is only for vscode users**

To activate your virtual environment run the following, use the command for your terminal.

bash

```
source venv/Scripts/activate
```

powershell
```
venv/Scripts/activate.ps1
```


After activating the virtual environment install the dependencies. To install the dependencies run.

```
pip install -r requirements.txt
```

**If during development you install packages run this in your terminal**
```
pip freeze > requirements.txt
```

Once you have installed all the packages onto your virtual enviroment you will need a .env file, you can find the contents needed in the .env file in the Contributing.md file. 

After all of this have been done you will need to setup your database, create a database and then run the following commands in your terminal. To setup the tables run

```
python app/db/schema.py
```

To add dummy data run.

```
python app/db/salt.py
```

Once all have been done check if everything is working well run.
```
python run.py
```

### CONTINUED DEVELOPMENT
When a teamate pushes, you need to add those changes made onto your machine or system, to do that run.

```
git pull origin main
```

If packages were added run.
```
pip install -r requirements.txt
```

And that is all you need to get started and continue developing for now.