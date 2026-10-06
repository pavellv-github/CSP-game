class_name BackendClient
extends RefCounted
## API client for Supabase (Auth, cloud save, content API via Edge Functions).
## Not used by the MVP: gameplay must work fully offline. The interface is fixed now so that
## cloud save / content download can be plugged in later without touching gameplay.
## The client never performs admin operations — those go through Edge Functions with RLS.

signal auth_state_changed(signed_in: bool)

var base_url: String = ""
var anon_key: String = ""


func is_configured() -> bool:
	return not base_url.is_empty() and not anon_key.is_empty()


func is_signed_in() -> bool:
	return false


## Phase 5: Supabase Auth.
func sign_in_anonymously() -> Error:
	return ERR_UNAVAILABLE


## Phase 5: returns {"content_version": int} from the content API.
func fetch_content_version() -> Dictionary:
	return {}


## Phase 5: uploads the local save (cloud save).
func push_save(_save_data: Dictionary) -> Error:
	return ERR_UNAVAILABLE
