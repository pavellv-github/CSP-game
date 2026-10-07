// Helpers for the "Персонажи — спрайты и механики" frame on the Miro board.
// Paste the whole file into javascript_exec on the board tab (the board page exposes the
// Miro Web SDK as window.miro), then call window.miroSync.* — see .claude/skills/miro-sync.
window.miroSync = (() => {
	const FRAME_ID = '3458764686306202137';
	// Frame top-left on the board; children coordinates are relative to it.
	const X0 = 3000, Y0 = -3000;
	const ROW = 1000, ROW_TOP = 250, STEP = 330;
	const HEROES = ['warrior', 'mage', 'healer', 'archer', 'hunter'];
	const STYLE = {
		start: ['round_rectangle', '#E8E2D6'], cd: ['round_rectangle', '#E8E2D6'],
		act: ['rectangle', '#FBE3C0'], dec: ['rhombus', '#FFF2A8'], skill: ['rectangle', '#D6E6FF'],
		res: ['round_rectangle', '#D5F0CF'], no: ['round_rectangle', '#F6D9D9'],
	};
	const rowTop = i => Y0 + ROW_TOP + i * ROW;
	const frame = () => miro.board.getById(FRAME_ID);

	async function node(kind, text, x, y) {
		const [shape, fillColor] = STYLE[kind];
		return miro.board.createShape({shape, content: `<p>${text}</p>`, x, y, width: 250, height: kind === 'dec' ? 180 : 120,
			style: {fillColor, fontSize: 16, textAlign: 'center', textAlignVertical: 'middle', borderColor: '#5b4a3a', borderWidth: 2, color: '#2b2118'}});
	}

	function link(a, b, caption, from = 'right', to = 'left') {
		return miro.board.createConnector({start: {item: a.id, snapTo: from}, end: {item: b.id, snapTo: to}, shape: 'elbowed',
			style: {strokeColor: '#5b4a3a', strokeWidth: 2, endStrokeCap: 'arrow'}, captions: caption ? [{content: caption}] : []});
	}

	// steps: [[kind, text, noBranchText?], ...]; a 'dec' step gets a red "нет" node below it.
	async function chain(steps, x, y) {
		const created = [];
		let prev = null;
		for (const [i, [kind, text, no]] of steps.entries()) {
			const n = await node(kind, text, x + i * STEP, y);
			created.push(n);
			if (prev) await link(prev.n, n, prev.kind === 'dec' ? 'да' : '');
			if (kind === 'dec') {
				const nn = await node('no', no || 'Ждём', x + i * STEP, y + 220);
				created.push(nn);
				await link(n, nn, 'нет', 'bottom', 'top');
			}
			prev = {n, kind};
		}
		return created;
	}

	// hero: {name, desc, stats: 'line|line', attack: steps, cd, skill: {start, steps, cd}}
	async function buildRow(i, hero) {
		const top = rowTop(i);
		const items = [];
		items.push(await miro.board.createText({content: `<p><strong>${hero.name}</strong> — ${hero.desc}</p>`, x: X0 + 400, y: top, width: 700, style: {fontSize: 40, color: '#2b2118', textAlign: 'left'}}));
		items.push(await miro.board.createStickyNote({content: `<p>${hero.stats.split('|').join('<br>')}</p>`, x: X0 + 900, y: top + 400, width: 300, style: {fillColor: 'light_yellow', textAlign: 'left', textAlignVertical: 'top'}}));
		items.push(...await chain([['start', 'Атака: каждый кадр'], ['dec', 'Автоатака вкл. и КД атаки готов?'], ...hero.attack, ['cd', hero.cd]], X0 + 1300, top + 150));
		items.push(...await chain([['start', hero.skill.start], ['dec', 'КД скилла готов?', 'Кнопка неактивна'], ...hero.skill.steps, ['cd', hero.skill.cd]], X0 + 1300, top + 600));
		const f = await frame();
		for (const it of items) await f.add(it);
		return items.length;
	}

	// Removes everything of row i except the sprite image (keepImage) — connectors go with their shapes.
	async function clearRow(i, {keepImage = true} = {}) {
		const f = await frame();
		const top = ROW_TOP + i * ROW - 60, bottom = top + ROW;
		const kids = (await f.getChildren()).filter(k => k.y >= top && k.y < bottom && !(keepImage && k.type === 'image'));
		const ids = new Set(kids.map(k => k.id));
		for (const c of await miro.board.get({type: 'connector'})) {
			if (ids.has(c.start?.item) || ids.has(c.end?.item)) await miro.board.remove(c);
		}
		for (const k of kids) await miro.board.remove(k);
		return kids.length;
	}

	// The sprite image currently in row i (or null).
	async function rowImage(i) {
		const f = await frame();
		const top = ROW_TOP + i * ROW - 60;
		return (await f.getChildren()).find(k => k.type === 'image' && k.y >= top && k.y < top + ROW) || null;
	}

	// Call right after Cmd+V: moves the just-pasted (selected) image into row i's sprite slot.
	async function placePasted(i) {
		await new Promise(r => setTimeout(r, 2500));
		const im = (await miro.board.getSelection()).find(s => s.type === 'image');
		if (!im) return 'no pasted image selected';
		const inFrame = !!im.parentId;
		im.width = 620;
		im.x = (inFrame ? 0 : X0) + 360;
		im.y = (inFrame ? 0 : Y0) + ROW_TOP + i * ROW + 470;
		await im.sync();
		if (!inFrame) await (await frame()).add(im);
		await miro.board.deselect();
		return {id: im.id, width: im.width, height: im.height};
	}

	function show(i) {
		return miro.board.viewport.set({viewport: {x: X0, y: rowTop(i) - 100, width: 3200, height: 1100}});
	}

	return {FRAME_ID, HEROES, node, link, chain, buildRow, clearRow, rowImage, placePasted, show};
})();
'miroSync ready';
