// Sample Power Query M (Mashup) for Dataflow Gen2
// This is a minimal example that creates a table from a list

let
    Source = {1..10},
    ConvertedToTable = Table.FromList(Source, Splitter.SplitByNothing(), null, null, ExtraValues.Error),
    RenamedColumns = Table.RenameColumns(ConvertedToTable,{{"Column1", "Number"}}),
    AddedColumn = Table.AddColumn(RenamedColumns, "Squared", each [Number] * [Number])
in
    AddedColumn
