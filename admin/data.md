- **distance_to_sign**: the signed forward distance from the ego vehicle's front bumper to the nearest road sign in the same lane. It is positive if the sign is ahead and negative if already passed. Returns infinity if no sign is found.
- **ego_speed**: the current speed of the ego vehicle, computed as the magnitude of its velocity vector.
- **distance_to_lead**: the distance from the ego vehicle's front bumper to the rear bumper of the nearest vehicle ahead in the same lane. Returns infinity if no vehicle is found.
- **threshold_safe**: the minimum distance considered safe under current driving and weather conditions, computed as half the ego speed scaled by a weather multiplier.
- **threshold_min**: the absolute minimum distance threshold below which an intervention is required, computed as a quarter of the ego speed scaled by the same weather multiplier.
- **ego_location**: the current position of the ego vehicle in the simulation world.
- **in_intersection**: a boolean indicating whether the ego vehicle is currently inside an intersection.
- **precedence**: a boolean indicating whether the ego vehicle has the right of way. It returns false if a vehicle is detected on the right or if a stop sign is within 30 meters and the ego is still moving.
broad_right_occupied: indicates whether a vehicle is present in a wide cone to the right of the ego (up to 30 meters forward and 3 meters laterally).
narrow_right_occupied: same as above but using a stricter cone (15 meters forward and 1.5 meters laterally).
- **min_line_distance**: the minimum lateral distance from the ego vehicle's edge to the nearest lane marking. Returns -1.0 if the vehicle has crossed a line, and 0.0 inside junctions.
- **line_continuous**: a boolean indicating whether the nearest lane marking is a solid line.
- **line_dashed**: a boolean indicating whether the nearest lane marking is a dashed line.
- **indicator**: the current state of the ego vehicle's turn indicator. Can be left, right, both, or None.
- **direction**: the current steering direction of the ego vehicle, either left or right.