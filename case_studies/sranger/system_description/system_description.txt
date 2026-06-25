SRanger is a small ground robot that travels in a straight line and turns when it detects an obstacle. The robot carries a single infrared (IR) distance sensor mounted facing forward, and a differential-drive motor pair that lets it command an arbitrary combination of linear velocity (lv) and angular velocity (av) at each control step. The robot has no operator control surface during normal operation — its movement is fully reactive to the sensor signal — but a system-level shutdown event (endTask) is available to halt it.

The SRanger controller is a reactive single-controller state machine with three operating modes:

- Moving: the robot drives forward at the configured linear velocity. On entering Moving, the controller issues a Move command with the configured linear velocity and zero angular velocity (forward only). The robot remains in Moving as long as the IR distance reading is above the obstacle-detection threshold.

- Turning: the robot rotates in place. On entering Turning, the controller issues a Move command with zero linear velocity and the configured angular velocity (turn only) and records the current time in a clock-reset variable. The robot remains in Turning until the elapsed time since the clock reset reaches the configured turn duration; at that point the controller transitions back to Moving (issuing a forward Move command on entry).

- Final: a terminal mode entered when the operator-level endTask event arrives. On entry, the controller issues a stop command (zero linear, zero angular).

The controller is driven by a small set of input events. The IR sensor surfaces an obstacle event whenever the measured distance crosses below the obstacle-detection threshold (obstacleThreshold = 0.5 m by default). The system framework delivers a tick event each control cycle. An endTask event from the operator-level shutdown channel terminates the controller into the Final state.

The controller's outputs are advisory motor commands to the differential-drive layer: Move(lv : real, av : real) carries a target linear and angular velocity. This is the only output the controller emits. The actuator stores the last-issued command for inspection.

The IR distance reading is exposed to the controller through a Sensor: distance() returns the latest IR measurement in metres. When the IR has not yet been initialised or no reading is available, the Sensor returns a large default value so that the obstacle-detection condition is not falsely triggered by missing data.

Constants used by the controller:
- moveVel: real = 1.0 (linear velocity when Moving, m/s)
- turnVel: real = 2.0 (angular velocity when Turning, rad/s)
- obstacleThreshold: real = 0.5 (IR-distance threshold for obstacle detection, metres)
- turnDuration: real = 2.0 (how long the robot remains in Turning before returning to Moving, seconds)

The clock variable clockResetTime: real records when the controller most recently entered the Turning state. The autonomous Turning → Moving transition fires when the time since clockResetTime is at or above turnDuration.

The original RoboChart model of SRanger is documented at the University of York RoboStar group: https://robostar.cs.york.ac.uk/case_studies/sranger/index.html. The requirements in this directory are derived from that source.
