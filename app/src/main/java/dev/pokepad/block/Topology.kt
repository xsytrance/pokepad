package dev.pokepad.block

/**
 * Connector-port topology → physical arrangement. The master block's topology
 * message lists every DNA connection as (device, port, device, port); the port
 * index says which EDGE of the block the snap is on, so a two-block arena can
 * be classified as SIDE_BY_SIDE (the classic left|right battle) or STACKED
 * (the vertical face-off: foe on the top block, your mon below, back view).
 *
 * Port→edge table = the JUCE BLOCKS data-sheet ordering for a Lightpad
 * (two DNA ports per edge, indexed clockwise from the north-west corner):
 *   0,1 = north · 2,3 = east · 4,5 = south · 6,7 = west
 * If real hardware disagrees, the raw ports are visible as "conn:d:p:d:p"
 * decode events (pokepad-conn log) — recalibrate this table from a capture.
 */
object Topology {
    enum class Edge { NORTH, EAST, SOUTH, WEST, UNKNOWN }
    enum class Arrangement { SIDE_BY_SIDE, STACKED, UNKNOWN }

    /** how the two blocks sit; masterOnTop only matters when STACKED */
    data class FaceOff(val arrangement: Arrangement, val masterOnTop: Boolean)

    val NONE = FaceOff(Arrangement.UNKNOWN, false)

    fun edgeOf(port: Int): Edge = when (port) {
        0, 1 -> Edge.NORTH
        2, 3 -> Edge.EAST
        4, 5 -> Edge.SOUTH
        6, 7 -> Edge.WEST
        else -> Edge.UNKNOWN
    }

    /** classify the master↔second connection (two-block arenas) */
    fun analyze(st: Blocks.State): FaceOff {
        val master = st.topologyIndex
        if (master < 0) return NONE
        val conn = st.connections.firstOrNull { it[0] == master || it[2] == master } ?: return NONE
        val masterPort = if (conn[0] == master) conn[1] else conn[3]
        return when (edgeOf(masterPort)) {
            Edge.NORTH -> FaceOff(Arrangement.STACKED, masterOnTop = false)   // other block sits above
            Edge.SOUTH -> FaceOff(Arrangement.STACKED, masterOnTop = true)
            Edge.EAST, Edge.WEST -> FaceOff(Arrangement.SIDE_BY_SIDE, false)
            Edge.UNKNOWN -> NONE
        }
    }
}
