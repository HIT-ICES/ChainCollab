import inherits from 'inherits';
import CommandInterceptor from 'diagram-js/lib/command/CommandInterceptor';
import { is } from 'bpmn-js/lib/util/ModelUtil';

/**
 * Ensures that ChoreographyActivity elements maintain their integrity
 * when DataAssociation connections are created
 * @constructor
 * @param {Injector} injector
 */
export default function DataAssociationBehavior(injector) {
  injector.invoke(CommandInterceptor, this);

  // Protect ChoreographyActivity AFTER creating DataAssociation connections
  this.postExecuted('connection.create', function (event) {
    const context = event.context;
    const connection = context.connection;
    const source = context.source;
    const target = context.target;

    // If a DataAssociation is connected to/from a ChoreographyActivity,
    // ensure the activity maintains its proper structure
    if (is(connection, 'bpmn:DataAssociation')) {
      console.log('[DataAssociationBehavior] postExecuted connection.create:');
      console.log('  Connection type:', connection.businessObject.$type);

      if (is(source, 'bpmn:ChoreographyActivity')) {
        console.log('  Source BEFORE ensure:', source.type, source.businessObject.$type);
        console.log('  Source bandShapes BEFORE:', source.bandShapes?.length);
        ensureChoreographyActivity(source);
        console.log('  Source AFTER ensure:', source.type, source.businessObject.$type);
        console.log('  Source bandShapes AFTER:', source.bandShapes?.length);
      }
      if (is(target, 'bpmn:ChoreographyActivity')) {
        console.log('  Target BEFORE ensure:', target.type, target.businessObject.$type);
        console.log('  Target bandShapes BEFORE:', target.bandShapes?.length);
        ensureChoreographyActivity(target);
        console.log('  Target AFTER ensure:', target.type, target.businessObject.$type);
        console.log('  Target bandShapes AFTER:', target.bandShapes?.length);
      }
    }
  });

  // Also protect when reconnecting
  this.postExecuted('connection.reconnect', function (event) {
    const context = event.context;
    const connection = context.connection;
    const source = context.newSource || context.source;
    const target = context.newTarget || context.target;

    if (is(connection, 'bpmn:DataAssociation')) {
      if (is(source, 'bpmn:ChoreographyActivity')) {
        ensureChoreographyActivity(source);
      }
      if (is(target, 'bpmn:ChoreographyActivity')) {
        ensureChoreographyActivity(target);
      }
    }
  });
}

function ensureChoreographyActivity(shape) {
  const businessObject = shape.businessObject;

  // Ensure the shape maintains its ChoreographyActivity properties
  if (is(businessObject, 'bpmn:ChoreographyActivity')) {
    // Make sure participantRef array exists
    if (!businessObject.participantRef) {
      businessObject.participantRef = [];
    }

    // Make sure bandShapes array exists
    if (!shape.bandShapes) {
      shape.bandShapes = [];
    }
  }
}

DataAssociationBehavior.$inject = ['injector'];
inherits(DataAssociationBehavior, CommandInterceptor);
