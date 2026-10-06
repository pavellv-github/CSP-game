class_name InputCommand
extends RefCounted
## Device-independent input for one physics frame.
## Touch controls, keyboard and gamepad all produce the same command, so the
## PlayerController never knows which device is used.

var move: Vector2 = Vector2.ZERO
var attack: bool = false
var skill: bool = false
var dash: bool = false
var interact: bool = false
var inventory: bool = false
var pause: bool = false
