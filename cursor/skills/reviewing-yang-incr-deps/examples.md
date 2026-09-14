# Golden: miss or not

Dirty root = outermost list around the **edit**. Skip-extra = LOCAL + LIST-SCOPE.

| id | Construct | Tool | Miss? | Why |
|----|-----------|------|-------|-----|
| A | `when derived-from-or-self(if:type, 'bbfift:vlan-sub-interface')` under `interfaces/interface` | LOCAL | no | Same row’s `if:type`. Edit another interface does not change this `when`. |
| B | leafref `../../component/name` on `hardware/component/contains-child` | LOCAL | **no** if `onu`/`interface` wraps `component`; **yes** if `component` **is** the outermost list | Schema LCA looks like (A): list *is* the LCA. Data reads every sibling `component`. Covered only when the dirty root is a list **above** `component`. |
| C | `must "/if:interfaces/if:interface[if:name=current()]/…"` | BOUNDED | no | Extra. (Create skip only if `creation_safe`; this shape of `must` often is not.) |
| D | leafref `"/xpongemtcont/tconts/tcont/name"` (no predicate) | UNBOUNDED | no | Extra. require-instance is `creation_safe` on create; delete/replace still extra. |
| E | `must "current() != ../from-interface"` | LOCAL | no | Same row sibling **leaf**, path does not re-enter the list from its parent. |

Without this skill, B is often called UNBOUNDED (“no key”). That is the wrong bucket **and** the wrong miss call: under an ONU it is skip-extra and still covered.
