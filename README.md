# The VehMocap Importer For Blender

This addon is a helper tool that allows you to import the JSON files exported by the [Vehicle Motion Capture MTA:SA resource](https://github.com/ThePortuguesePlayer/VehMocap) as animation into Blender 2.80 and up.

## Installation

Install the .py file like any other Blender addon.
Once activated, you can find it on your 3D Viewport's side panel, under the Animation tab.
It is assumed you already have a way of importing DFF models into Blender, such as by using the [DragonFF addon](https://github.com/Parik27/DragonFF).

## Usage

. Import a vehicle into your scene.
. Navigate to the VehMocap Tool window, under the Animation tab on the 3D Viewport side panel and input the path to your JSON file.
. Once your JSON file is validated, select your vehicle's main dummy/empty.
. If your vehicle is a standard GTA:SA model, press Import Animation at the prefered frame. If not, select your other dummies beforehand.
. Progress will be printed to the console.