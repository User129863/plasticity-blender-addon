# plasticity-blender-addon

Experimental Plasticity blender addon to send facet data over websockets

Various QOL improvements to the Plasticity Bridge Blender add-on:

- Consolidated Mark Sharp and Mark Sharp at boundaries into a single operator (AutoMarkEdgesOperator) with options to mark selection as Hard Edges or UV Seams (Mark Sharp, Mark Seam).
- Added functionality: Smart Edges Marking - Only works on entire mesh selection and not individually selected polygons that are part of a Plasticity group. Will mark edges as Sharp or UV seam using the logic of MarkSharpEdgesForPlasticityGroupsWithSplitNormalsOperator.
- Added functionality to arbitrarily select polygons that are part of Plasticity surface groups and mark their boundaries instead of marking boundaries of individual Plasticity surfaces (for mark as Sharp and with added UV seams functionality).
- Added functionality to merge existing UV seams based on arbitrary Plasticity group polygon selection.
- Added functionality to select Plasticity groups edges.
- Changed default port from 8080 to 8090 (conflicting with some AV software).
- Exposed prop_surface_angle_tolerance parameter, allowing users to have more control when re-meshing and wanting to keep small objects having smooth curves.

Always make sure that you remesh the imported CAD data from Plasticity at least once, otherwise most of the Brigde features won't work as expected.
