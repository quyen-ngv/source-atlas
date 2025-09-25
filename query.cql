MATCH (endpoint)
WHERE endpoint.class_name = "com.edu.onestudy.entity.Resource"

CALL apoc.path.expandConfig(endpoint, {
  relationshipFilter: "<CALL|<USE|IMPLEMENT",
  minLevel: 1,
  maxLevel: 100,
  bfs: true,
  uniqueness: "NODE_GLOBAL",
  filterStartNode: false
}) YIELD path

WITH endpoint,
     path,
     nodes(path) AS node_list,
     relationships(path) AS rel_list,
     [i IN range(0, size(relationships(path))-1) |
        CASE
          WHEN type(relationships(path)[i]) IN ['CALL','USE','IMPLEMENT'] THEN nodes(path)[i+1]
          ELSE null
        END
     ] AS filtered_nodes

RETURN endpoint,
       [node IN filtered_nodes WHERE node IS NOT NULL] AS callers,
       length(path) AS depth
ORDER BY depth ASC;

-----------------------
WITH [
  {class_name:'com.example.springdemo.event.UserEventConsumer'}
] AS targets

MATCH (endpoint:EndpointNode)
WHERE any(t IN targets WHERE
    t.class_name = endpoint.class_name AND t.method_name = endpoint.method_name)

CALL apoc.path.expandConfig(endpoint, {
  relationshipFilter: "CALL>|<IMPLEMENT|<EXTEND|USE>",
  minLevel: 1,
  maxLevel: 20,
  bfs: true,
  uniqueness: "NODE_GLOBAL",
  filterStartNode: false
}) YIELD path

WITH endpoint, path,
     nodes(path) AS node_list,
     relationships(path) AS rel_list

WITH endpoint, path, node_list, rel_list,
     [i IN range(0, size(rel_list)-1) |
        CASE
          WHEN type(rel_list[i]) = 'CALL'
               AND node_list[i+1].method_name IS NOT NULL
          THEN node_list[i+1]

          WHEN type(rel_list[i]) IN ['IMPLEMENT', 'EXTEND']
               AND node_list[i+1].method_name IS NOT NULL
               AND node_list[i].method_name IS NOT NULL
          THEN node_list[i+1]

          WHEN type(rel_list[i]) = 'USE'
               AND node_list[i+1].method_name IS NULL
          THEN node_list[i+1]

          ELSE null
        END
     ] AS filtered_nodes


RETURN endpoint, path,
       [node IN filtered_nodes WHERE node IS NOT NULL] AS visited_nodes_per_path
ORDER BY path;







