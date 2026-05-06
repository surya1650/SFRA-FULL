# SFRA-FULL: Multi-Trace Transformer Diagnostic Suite

## 1. Project Overview & Objective
This document outlines the functional requirements and architectural logic for the `SFRA-FULL` repository. Extending the single-trace capabilities of the original `SFRA` project, this suite is designed to automate the ingestion, metadata assignment, and comparative analysis of multiple Sweep Frequency Response Analysis (SFRA) traces based on international standards (e.g., IEEE C57.149, IEC 60076-18).

## 2. File Handling & Parsing Engine
The software must support bulk imports and extract frequency, magnitude (dB), and phase data from various manufacturer-specific formats:
* **Standard Single Files:** `.xml`, `.csv`, `.txt`
* **Vendor-Specific Single Files:** `.xfra`, `.sfra` (Doble)
* **Container/Archive Formats:** `.frax` (Megger - extracting all files contained within the folder/archive).

**Workflow:** The application will list all files extracted from the uploaded test set (e.g., parsing a `.frax` file to show all internal traces) before moving to metadata assignment.

## 3. Metadata & Input Assignment
To accurately pair Reference and Tested traces, the UI/logic must allow users to assign or verify the following parameters for each extracted trace:
* **Test Type** (e.g., End-to-End, Capacitive Inter-winding, Inductive Inter-winding)
* **Open/Short Condition** (e.g., LV Open, LV Shorted)
* **Phase** (R, Y, B / A, B, C)
* **Winding** (HV, LV, IV, Tertiary)
* **Reference Terminal**
* **Response Terminal**
* **Shorted Terminals**
* **Grounded Terminals**
* **Tap Position** (Current)
* **Previous OLTC Tap Position**

## 4. Core Analytical Features
Once metadata is assigned and Reference/Tested traces are paired for a specific combination (e.g., HV R-Phase End-to-End, LV Open), the engine performs the following:

### A. Visualization & Plotting
* **Superimposed Plots:** Overlays the Magnitude and Phase plots of both the Reference and Tested traces.
* **Difference Plots:** Calculates and plots the $\Delta dB$ (Magnitude Difference) across the frequency spectrum.
* **Frequency Banding:** Visual plotting of standard frequency sub-bands (Low, Medium, High) to isolate core, winding structure, and connection anomalies.

### B. Resonance & Feature Extraction
* **Peak and Valley Detection:** Automates the identification of resonance ($f_{res}$) and anti-resonance points.
* **Tabular Comparison:** Generates a table comparing frequency (Hz) and magnitude (dB) at peaks and valleys for both Reference and Tested traces, calculating the shifts.

### C. Mathematical Indices & Diagnostics
* Calculates statistical indices per standards, including **Cross-Correlation Coefficient (CC)** and **Difference/Logarithmic Error (DL/ASLE)**.
* **Automated Diagnostics:** Assigns a "Type of Problem" (e.g., Core Deformation, Winding Movement, Shorted Turns) based on the calculated index factors across specific frequency bands.

## 5. Multi-Phase Summary & Reporting
If all phases (R, Y, B) are analyzed, the system aggregates the data:
* **Phase Comparison Table:** Cross-compares dB differences at peaks and valleys across all phases.
* **Index Summary:** A consolidated table showing mathematical indices (CC, DL) for all phases.
* **Final Master Table:** A comprehensive summary detailing the status, index results, and diagnostic remarks for *every* analyzed combination.

## 6. Advanced Modeling (Inherited from Single-Trace Repo)
The system integrates advanced mathematical modeling for each selected combination:
* **Transfer Function Plotting**
* **Pole-Zero Fitting**
* **RLC Parameter Design:** Synthesizing equivalent electrical circuit parameters ($R, L, C$) based on the frequency response to simulate the physical winding characteristics.

## 7. Execution Robustness & Edge Cases
* **Partial Data Execution:** The analysis pipeline is completely modular. It does **not** require a full set of combinations (e.g., all 9 or 12 traces) to run. 
* If only a single combination (or even a single trace) is uploaded, the tool gracefully degrades, analyzing and reporting on whatever data is available without throwing dependency errors.
