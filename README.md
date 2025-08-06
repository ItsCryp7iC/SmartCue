# SmartCue - Pool Game Guideline Overlay

![SmartCue Screenshot](https://i.imgur.com/yxHknsn.png) <!-- Replace with a URL to your screenshot -->

SmartCue is a customizable overlay for PC pool games. It provides visual aids, including aiming lines to pockets and accurate multi-bounce predictions, to help players improve their shots and understand ball physics.

---

## Features

* **Aiming Lines:** Displays lines from the object ball to all six pockets.
* **Accurate Bounce Prediction:** Simulates and visualizes up to 5 bounces off the cushions, accounting for ball radius.
* **Fully Customizable UI:** A draggable settings panel allows you to control the visibility, color, size, and transparency of every visual element.
* **Persistent Settings:** Your layout and theme settings are automatically saved to a `settings.json` file and loaded on startup.
* **Precise Controls:** Use the mouse or keyboard (tab and arrow keys) for fine-tuned adjustments of the table border and ball positions.
* **Standalone Application:** Packaged into a single `.exe` file that runs without needing Python or any dependencies installed.

---

## How to Use (For Users)

1.  Go to the [Releases page](https://github.com/ItsCryp7iC/SmartCue/releases). <!-- Replace with your GitHub username and repo name -->
2.  Download the latest `SmartCue.exe` file.
3.  Run `SmartCue.exe`. The overlay and settings panel will appear.
4.  Drag the yellow square handles to align the overlay with your in-game pool table.
5.  Use the settings panel to customize the look and feel to your preference.

---

## For Developers

If you want to run or modify the source code:

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/ItsCryp7iC/SmartCue.git](https://github.com/ItsCryp7iC/SmartCue.git)
    cd SmartCue
    ```

2.  **Install dependencies:**
    ```bash
    pip install PyQt5 pywin32
    ```

3.  **Run the script:**
    ```bash
    python overlay.py
    ```

---

## Controls

* **F7:** Toggle Border Resize Mode.
* **F8:** Toggle Interactive Mode (makes the overlay click-through).
* **Arrow Keys:** Move the selected ball or border handle by 1 pixel.
* **Shift + Arrow Keys:** Move the selected ball or border handle by 5 pixels.
* **Tab:** Switch focus between balls or between border resize handles.
* **Mouse Drag:** Move balls or resize the border.
* **ESC:** Close the application.

---

## Acknowledgements

This project was developed with assistance from Google's AI **Gemini 2.5 Pro**. The core logic, features, and final implementation were directed and completed by the project author.

---

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
