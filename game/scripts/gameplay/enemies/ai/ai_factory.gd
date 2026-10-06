class_name AiFactory
extends RefCounted
## Maps `ai_type` from enemy data to a behaviour. New enemies reuse existing AIs;
## a new AI is one class + one line here.


static func create(ai_type: String) -> EnemyAI:
	match ai_type:
		"chase":
			return ChaseAI.new()
		"melee":
			return MeleeAI.new()
		"ranged":
			return RangedAI.new()
		"passive":
			return PassiveAI.new()
		"boss":
			return BossAI.new()
		_:
			push_warning("[AI] unknown ai_type '%s', falling back to chase" % ai_type)
			return ChaseAI.new()
