// The module 'vscode' contains the VS Code extensibility API

// Import the module and reference it with the alias vscode in your code below
const vscode = require('vscode');
const path = require('path');
// This method is called when your extension is activated
// Your extension is activated the very first time the command is executed


/**
 * @param {vscode.ExtensionContext} context
 */

function activate(context) {
	console.log('Congratulations, your extension "jsoncodeeditor" is now active!');
	const fabricDocumentSelector = [
		{ language: 'jsonc', scheme: '*', pattern: "**/snippet.json" }
	];
	context.subscriptions.push(vscode.languages.registerCodeLensProvider(fabricDocumentSelector, {
		provideCodeLenses(document, token) {
			const codeLenses = [];
			const text = document.getText();
			const jsonObject = JSON.parse(text);
			const regex = /"([^"]+)":/g;
			let match;
			while ((match = regex.exec(text)) !== null) {
				const key = match[1];
				const startPosition = document.positionAt(match.index);
				const range = new vscode.Range(startPosition, startPosition.translate(0, key.length + 1));
				const editCommand = {
					title: "Edit",
					command: "extension.editKey",
					arguments: [key, jsonObject, document.uri],
				};
				codeLenses.push(new vscode.CodeLens(range, editCommand));

				// Delete command
				const deleteCommand = {
					title: "Delete",
					command: "extension.deleteKey",
					arguments: [key, jsonObject, document.uri],
				};
				codeLenses.push(new vscode.CodeLens(range, deleteCommand));
			}
			return codeLenses;
		},

		resolveCodeLens(codeLens, token) {
			return codeLens;
		}
	}));

	context.subscriptions.push(vscode.commands.registerCommand("extension.TreeView", () => {
		// Add a sub Tree View
		const treeDataProvider = {
			getChildren: () => {
				const text = vscode.window.activeTextEditor.document.getText();
				const jsonObject = JSON.parse(text);
				return Object.keys(jsonObject);
			},
			getTreeItem: (element) => {
				const treeItem = new vscode.TreeItem(element);
				// tree item with button
				treeItem.command = {
					command: "extension.editKey",
					title: "Edit",
					arguments: [element, JSON.parse(vscode.window.activeTextEditor.document.getText()), vscode.window.activeTextEditor.document.uri]
				};
				treeItem.tooltip = "Click to edit";

				// Additional Delete Button 
				treeItem.contextValue = "delete";


				return treeItem;
			}
		};

		vscode.window.createTreeView("JsonCodeEditor", { treeDataProvider });

	}));


	let listeners = []
	let fileToDelete = null

	context.subscriptions.push(vscode.commands.registerCommand("extension.editKey", async (key, jsonObject, uri) => {
		// release old listener
		listeners.forEach(
			(listener) => listener.dispose()
		)
		listeners = []
		if (fileToDelete) {
			vscode.workspace.fs.delete(fileToDelete)
			fileToDelete = null
		}

		// key end with Frame?
		isEndWithFrame = key.endsWith("Frame")
		// read {xxx} as $xxx^(dont change {{xxx}}),  {{ as {, }} as }, differentiate { and {{ , don't confuse with it

		// open a titled document
		value = isEndWithFrame? jsonObject[key].replace(/(?<!{){([^{}]+)}/g, "#$1#").replace(/{{/g, "{").replace(/}}/g, "}"):jsonObject[key]
		doc_path = path.join(path.dirname(uri.fsPath), key + ".go");
		const encoder = new TextEncoder();
		await vscode.workspace.fs.writeFile(vscode.Uri.file(doc_path), encoder.encode(value));
		const doc = await vscode.workspace.openTextDocument(doc_path)
		const editor = await vscode.window.showTextDocument(doc, vscode.ViewColumn.Beside);

		// on save, update the uri document. need listener for save. and uri is a json, not a go
		const saveListener = vscode.workspace.onDidSaveTextDocument((e) => {
			// update the jsonObject and save it to the uri
			if (e.fileName !== doc_path) {
				return;
			}

			// match { to {{, } to }} , then #
			value = isEndWithFrame? e.getText().replace(/{/g, "{{").replace(/}/g, "}}").replace(/#([^#]+)#/g, "{$1}"):e.getText()
			console.log(isEndWithFrame)
			console.log(e.getText())
			console.log(value)
			jsonObject[key] = value
			const encoder = new TextEncoder();
			vscode.workspace.fs.writeFile(uri, encoder.encode(JSON.stringify(jsonObject, null, 2)));
		});

		// close the listener when the editor is closed, and delete the file

		const closeListener = vscode.window.tabGroups.onDidChangeTabs(() => {
			groups = vscode.window.tabGroups.all
			var flag = false
			groups.forEach((group) => {
				group.tabs.forEach(element => {
					if (flag) return
					if (element.label === key + ".go") {
						flag = true
						return
					}
				})
			})
			if (flag) return
			listeners.forEach(
				(listener) => listener.dispose()
			)
			listeners = []
			if (fileToDelete) {
				vscode.workspace.fs.delete(fileToDelete)
				fileToDelete = null
			}
		})
		listeners.push(
			saveListener,
			closeListener
		)
		fileToDelete = vscode.Uri.file(doc_path)

	}));

	context.subscriptions.push(vscode.commands.registerCommand("extension.deleteKey", async (key, jsonObject, uri) => {
		delete jsonObject[key];
		const encoder = new TextEncoder();
		await vscode.workspace.fs.writeFile(uri, encoder.encode(JSON.stringify(jsonObject, null, 2)));
	})
	);

	// add key command
	context.subscriptions.push(vscode.commands.registerCommand("extension.addKey", async (key, jsonObject, uri) => {
		jsonObject[key] = "";
		const encoder = new TextEncoder();
		await vscode.workspace.fs.writeFile(uri, encoder.encode(JSON.stringify(jsonObject, null, 2)));
	}
	));

}

// This method is called when your extension is deactivated
function deactivate() { }

module.exports = {
	activate,
	deactivate
}
