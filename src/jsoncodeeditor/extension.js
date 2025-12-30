const vscode = require('vscode');
const path = require('path');
const { TextEncoder } = require('util');

const DOCUMENT_SELECTOR = [
	{ language: 'jsonc', scheme: '*', pattern: '**/snippet.json' }
];

class JsonCodeLensProvider {
	provideCodeLenses(document) {
		const parsed = safeParse(document);
		if (!parsed) {
			return [];
		}

		const lenses = [];
		const regex = /"([^"\n]+)"\s*:/g;
		const text = document.getText();
		let match;
		while ((match = regex.exec(text)) !== null) {
			const key = match[1];
			const start = document.positionAt(match.index + 1);
			const range = new vscode.Range(start, start.translate(0, key.length));
			lenses.push(new vscode.CodeLens(range, {
				title: 'Edit | Delete',
				command: 'extension.keyActions',
				arguments: [document.uri, key],
			}));
		}

		return lenses;
	}
}

class JsonTreeDataProvider {
	constructor() {
		this._onDidChangeTreeData = new vscode.EventEmitter();
		this.onDidChangeTreeData = this._onDidChangeTreeData.event;
	}

	refresh() {
		this._onDidChangeTreeData.fire();
	}

	getChildren() {
		const document = getActiveSnippetDocument();
		const parsed = document ? safeParse(document) : null;
		return parsed ? Object.keys(parsed) : [];
	}

	getTreeItem(element) {
		const treeItem = new vscode.TreeItem(element);
		const document = getActiveSnippetDocument();
		if (document) {
			treeItem.command = {
				command: 'extension.editKey',
				title: 'Edit',
				arguments: [document.uri, element],
			};
		}
		treeItem.contextValue = 'jsonEntry';
		return treeItem;
	}
}

class SnippetEditorManager {
	constructor() {
		this.activeEditor = null;
	}

	async open(uri, key) {
		const document = await vscode.workspace.openTextDocument(uri);
		const jsonObject = safeParse(document);
		if (!jsonObject) {
			return;
		}
		if (!(key in jsonObject)) {
			vscode.window.showWarningMessage(`Key "${key}" does not exist in snippet.`);
			return;
		}

		await this.disposeActiveEditor();
		const isFrame = key.endsWith('Frame');
		const prepared = prepareValueForEditing(jsonObject[key] ?? '', isFrame);
		const tempPath = path.join(path.dirname(uri.fsPath), `${key}.tmp`);
		const tempUri = vscode.Uri.file(tempPath);
		await writeTextFile(tempUri, prepared);
		const doc = await vscode.workspace.openTextDocument(tempUri);
		await vscode.window.showTextDocument(doc, vscode.ViewColumn.Beside);

		const saveDisposable = vscode.workspace.onDidSaveTextDocument(async savedDoc => {
			if (savedDoc.uri.fsPath !== tempPath) {
				return;
			}
			const updatedDoc = await vscode.workspace.openTextDocument(uri);
			const currentObject = safeParse(updatedDoc);
			if (!currentObject) {
				return;
			}
			currentObject[key] = prepareValueForSave(savedDoc.getText(), isFrame);
			await writeJson(uri, currentObject);
		});

		const closeDisposable = vscode.workspace.onDidCloseTextDocument(closedDoc => {
			if (closedDoc.uri.fsPath === tempPath) {
				this.disposeActiveEditor();
			}
		});

		this.activeEditor = {
			tempUri,
			disposables: [saveDisposable, closeDisposable],
		};
	}

	async disposeActiveEditor() {
		if (!this.activeEditor) {
			return;
		}
		this.activeEditor.disposables.forEach(d => d.dispose());
		try {
			await vscode.workspace.fs.delete(this.activeEditor.tempUri);
		} catch {
			// Ignore deletion errors (file might already be gone)
		}
		this.activeEditor = null;
	}

	dispose() {
		return this.disposeActiveEditor();
	}
}

function getActiveSnippetDocument() {
	const editor = vscode.window.activeTextEditor;
	if (!editor) {
		return null;
	}
	return isSnippetDocument(editor.document) ? editor.document : null;
}

function isSnippetDocument(document) {
	return document.fileName.endsWith('snippet.json');
}

function safeParse(document) {
	try {
		return JSON.parse(document.getText());
	} catch (error) {
		vscode.window.showErrorMessage(`SnippetSmith: Unable to parse ${path.basename(document.fileName)}. ${error.message}`);
		return null;
	}
}

function prepareValueForEditing(value, isFrame) {
	if (!isFrame) {
		return value ?? '';
	}
	return (value ?? '')
		.replace(/(?<!{){([^{}]+)}/g, '#$1#')
		.replace(/{{/g, '{')
		.replace(/}}/g, '}');
}

function prepareValueForSave(value, isFrame) {
	if (!isFrame) {
		return value;
	}
	return value
		.replace(/{/g, '{{')
		.replace(/}/g, '}}')
		.replace(/#([^#]+)#/g, '{$1}');
}

async function writeTextFile(uri, content) {
	const encoder = new TextEncoder();
	await vscode.workspace.fs.writeFile(uri, encoder.encode(content));
}

async function writeJson(uri, jsonObject) {
	await writeTextFile(uri, JSON.stringify(jsonObject, null, 2));
}

async function deleteKey(uri, key) {
	const document = await vscode.workspace.openTextDocument(uri);
	const jsonObject = safeParse(document);
	if (!jsonObject) {
		return;
	}
	if (!(key in jsonObject)) {
		vscode.window.showWarningMessage(`Key "${key}" does not exist.`);
		return;
	}
	delete jsonObject[key];
	await writeJson(uri, jsonObject);
}

async function addKey(uri) {
	let targetUri = uri;
	if (!targetUri) {
		const activeDoc = getActiveSnippetDocument();
		targetUri = activeDoc?.uri;
	}
	if (!targetUri) {
		vscode.window.showWarningMessage('No snippet.json document is active.');
		return;
	}
	const document = await vscode.workspace.openTextDocument(targetUri);
	const jsonObject = safeParse(document);
	if (!jsonObject) {
		return;
	}
	const key = await vscode.window.showInputBox({ prompt: 'Enter a new key for snippet.json' });
	if (!key) {
		return;
	}
	if (key in jsonObject) {
		vscode.window.showWarningMessage(`Key "${key}" already exists.`);
		return;
	}
	jsonObject[key] = '';
	await writeJson(targetUri, jsonObject);
}

/**
 * @param {vscode.ExtensionContext} context
 */
function activate(context) {
	const editorManager = new SnippetEditorManager();
	context.subscriptions.push(editorManager);

	context.subscriptions.push(
		vscode.languages.registerCodeLensProvider(DOCUMENT_SELECTOR, new JsonCodeLensProvider())
	);

	const treeProvider = new JsonTreeDataProvider();
	const treeView = vscode.window.createTreeView('SnippetSmithView', { treeDataProvider: treeProvider });
	context.subscriptions.push(treeView);

	context.subscriptions.push(
		vscode.commands.registerCommand('extension.TreeView', () => treeProvider.refresh())
	);

	context.subscriptions.push(
		vscode.workspace.onDidChangeTextDocument(event => {
			if (isSnippetDocument(event.document)) {
				treeProvider.refresh();
			}
		})
	);

	context.subscriptions.push(
		vscode.window.onDidChangeActiveTextEditor(editor => {
			if (!editor || isSnippetDocument(editor.document)) {
				treeProvider.refresh();
			}
		})
	);

	context.subscriptions.push(
		vscode.commands.registerCommand('extension.editKey', (uri, key) => editorManager.open(uri, key))
	);

	context.subscriptions.push(
		vscode.commands.registerCommand('extension.deleteKey', (uri, key) => deleteKey(uri, key))
	);

	context.subscriptions.push(
		vscode.commands.registerCommand('extension.addKey', uri => addKey(uri))
	);

	context.subscriptions.push(
		vscode.commands.registerCommand('extension.keyActions', async (uri, key) => {
			const action = await vscode.window.showQuickPick(['Edit', 'Delete'], {
				placeHolder: `Choose action for "${key}"`,
			});
			if (!action) {
				return;
			}
			if (action === 'Edit') {
				return vscode.commands.executeCommand('extension.editKey', uri, key);
			}
			return vscode.commands.executeCommand('extension.deleteKey', uri, key);
		})
	);
}

function deactivate() { }

module.exports = {
	activate,
	deactivate,
};
