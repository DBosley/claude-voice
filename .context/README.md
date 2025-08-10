# Claude Voice Context Directory

This is a sandboxed directory for Claude voice interactions. Files created and modified here are isolated from the rest of the system.

## What Claude CAN do here:
- Read files
- Write new files
- Edit existing files
- Search through files
- List directory contents

## What Claude CANNOT do here:
- Execute bash commands
- Use git
- Access the network (curl, wget)
- Run system commands
- Access files outside this directory
- Change file permissions

## Usage
When you use voice mode, Claude operates within this directory as its working space. You can ask it to:
- Create documents
- Write code snippets
- Organize notes
- Process text files
- Answer questions based on files here

All work stays safely contained within `.context/`