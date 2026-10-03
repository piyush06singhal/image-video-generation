# Evaluation & Quality Framework

## 1. Multi-Dimensional Quality Rubric

The system establishes a 6-dimension evaluation framework for real estate walkthrough generation. Each dimension is scored on a **1 to 5 continuous integer scale**:

| Dimension | Description | Benchmark Threshold |
|---|---|---|
| **1. Visual Quality & Realism** | Photorealistic rendering fidelity, crisp architectural details, lighting naturalness, absence of blur. | ≥ 4.0 |
| **2. Property Consistency** | Faithful preservation of layout, furniture, materials, wall positions, and color palettes from source photos. | ≥ 4.0 |
| **3. Scene Ordering & Flow** | Architectural walkthrough path logic (Exterior → Foyer → Living → Dining → Kitchen → Bedrooms → Bathrooms → Exterior/Balcony). | ≥ 4.5 |
| **4. Motion Naturalness** | Smooth, controlled camera trajectories without disorienting sudden turns, tilt jitters, or excessive speed. | ≥ 4.0 |
| **5. Temporal Stability** | Absence of morphing, flickering textures, warping objects, appearing/disappearing items, or structural hallucinations. | ≥ 3.5 |
| **6. Practical Usefulness** | Practical value as a real estate marketing, listing showcase, or buyer inspection tool. | ≥ 4.0 |

---

## 2. Automated System Verification Checks

The backend automatically executes non-subjective technical verification checks:

1. **Scene Analysis Completeness (`all_scenes_analyzed`):**
   - Reports whether all uploaded property photographs have completed multimodal visual classification for the current project.
2. **Clip Generation Completeness (`all_clips_generated`):**
   - Verifies that an approved video clip exists for every planned scene in the sequence. Reports missing scenes if any.
3. **Walkthrough Assembly Validation (`video_assembled`):**
   - Confirms the final concatenated MP4 video file exists on disk.
4. **Stream & Codec Integrity (`has_corrupted_output`):**
   - Probes the final video container and decodes an initial frame to check that the generated file is readable and has expected metadata. This is a validation check, not a guarantee of perceptual quality.
5. **Plan Synchronization Status (`is_outdated_relative_to_plan`):**
   - Verifies if the assembled video matches the SHA-256 fingerprint of the latest saved generation plan.

---

## 3. Per-Scene Review & Defect Tagging

Reviewers can inspect each individual room and assign one of three quality statuses:
- **`Acceptable`**: Scene clip meets publication quality standards.
- **`Needs Review`**: Minor visual artifacts or timing issues observed.
- **`Failed`**: Severe structural hallucination, unnatural warp, or corrupted stream.

### Standardized Defect Flags:
- `geometry_distortion`: Walls, doors, or window frames warp during camera motion.
- `object_inconsistency`: Furniture or appliances shift shape, color, or location.
- `flickering`: High-frequency texture or shadow shimmer between frames.
- `unnatural_motion`: Jerky, excessively fast, or non-linear camera velocity.
- `lighting_drift`: Unnatural color temperature shifts or flashing light sources.

---

## 4. Technical Quality Report

The system compiles an exportable technical audit report combining system specifications, automated verification checks, arithmetic evaluation averages, and per-scene reviewer comments into a structured text report.
