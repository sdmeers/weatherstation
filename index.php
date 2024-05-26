<?php 
// Enable error reporting
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);
error_reporting(E_ALL);

/*
    // Start MySQL Connection
     include('connect.php'); 
*/
?>

<!DOCTYPE html>
<html>
<head>
    <title>Raspberry Pi Weather Log</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css">
    <script src="https://kit.fontawesome.com/e1d7788428.js" crossorigin="anonymous"></script>
    <style type="text/css">
        /* Existing styles */
        .table_titles, .table_cells_odd, .table_cells_even {
            padding-right: 20px;
            padding-left: 20px;
            color: #000;
        }
        .table_titles {
            color: #FFF;
            background-color: #666;
        }
        .table_cells_odd {
            background-color: #CCC;
        }
        .table_cells_even {
            background-color: #FAFAFA;
        }
        .pagination-link {
            font-size: 30px; /* Larger font size */
            color: #007bff; /* A clearer color, you can choose what you prefer */
            padding: 2px; /* Additional padding for easier clicking */
            text-decoration: none; /* Optional: Removes underline from links */
        }

        .pagination-link:hover {
            color: #0056b3; /* Color change on hover for better user experience */
        }

        .disabled {
            font-size: 30px; /* Larger font size */
            color: #ccc;
            padding: 2px;
        }

        table {
            border: 2px solid #333;
        }
        body {
            font-family: "Trebuchet MS", Arial;
        }

        /* Responsive styles */
        @media screen and (max-width: 600px) {
            table {
                width: 100%;
                display: block;
                overflow-x: auto;
            }
            .table_titles, .table_cells_odd, .table_cells_even {
                padding: 10px;
            }
            .pagination-link {
                font-size: 30px; /* Even larger size for mobile */
                padding: 5px; /* Larger padding for touch screens */
            }
            body {
                font-size: 16px;
            }
            a, button {
                padding: 15px;
                font-size: 16px;
            }
        }

        /* New styles for navbar */
        .navbar-custom {
            display: flex;
            justify-content: space-between;
            background-color: black;
            color: white;
            padding: 8px 16px; /* Adjusted padding for height */
            z-index: 4;
            position: fixed;
            width: 100%;
            top: 0;
            font-family: 'Raleway', sans-serif;
            font-size: 18px;
            line-height: 1.5;
        }
        .navbar-custom a {
            text-decoration: none;
            color: white !important;
            font-family: 'Raleway', sans-serif;
            font-size: 18px;
        }
        .navbar-custom i {
            color: white;
            margin-right: 10px;
            font-size: 18px;
        }

        /* Responsive text for navbar links */
        .navbar-custom a[data-title]::after {
            content: attr(data-title);
            display: none;
        }
        @media screen and (max-width: 600px) {
            .navbar-custom a[data-title]::before {
                content: attr(data-title);
                display: inline;
            }
            .navbar-custom a[data-title] span {
                display: none;
            }
        }
    </style>
</head>

<body>
    <!-- Navigation bar -->
    <div class="navbar-custom">
        <a href="http://192.168.50.51:5000" data-title="Weather Summary"><i class="fa-solid fa-magnifying-glass-chart"></i> <span>Weather Summary</span></a>
        <a href="http://192.168.50.51:5001" data-title="Weather Dashboard"><i class="fa-solid fa-database"></i> <span>Weather Dashboard</span></a>
    </div>

    <h1 style="padding-top: 60px;">Raspberry Pi Weather Log</h1> <!-- Added padding to account for fixed navbar -->

<table border="0" cellspacing="0" cellpadding="4">
    <tr>
        <td class="table_titles">id</td>
        <td class="table_titles">Timestamp (local)</td>
        <td class="table_titles">Temperature (C)</td>
        <td class="table_titles">Pressure (hPa)</td>
        <td class="table_titles">Humidity (%)</td>
        <td class="table_titles">Rain (mm)</td>
        <td class="table_titles">Rain rate (mm/s)</td>
        <td class="table_titles">Luminance (lux)</td>
        <td class="table_titles">Wind Speed (m/s)</td>
        <td class="table_titles">Wind Direction (deg)</td>
        <td class="table_titles">Day</td>
        <td class="table_titles">Week</td>
        <td class="table_titles">Month</td>
        <td class="table_titles">Year</td>
    </tr>

    <?php
    
    require_once '/home/pi/weather/config.php';
    
    $mysqli = new mysqli('localhost', $username, $password, $databasename);
    if ($mysqli->connect_error) {
        die("Connection failed: " . $mysqli->connect_error);
    }
    // Find out how many items are in the table
    $total = $mysqli->query("SELECT COUNT(*) AS total FROM data")->fetch_assoc()['total'];

    // How many items to list per page
    $limit = 96;

    // How many pages will there be
    $pages = ceil($total / $limit);

    // What page are we currently on?
    $page = min($pages, filter_input(INPUT_GET, 'page', FILTER_VALIDATE_INT, array(
        'options' => array(
            'default'   => 1,
            'min_range' => 1,
        ),
    )));

    // Calculate the offset for the query
    $offset = ($page - 1)  * $limit;

    // The "back" link
    //$prevlink = ($page > 1) ? '<a href="?page=1" title="First page">&laquo;</a> <a href="?page=' . ($page - 1) . '" title="Previous page">&lsaquo;</a>' : '<span class="disabled">&laquo;</span> <span class="disabled">&lsaquo;</span>';
    $prevlink = ($page > 1) ? '<a href="?page=1" title="First page" class="pagination-link">&laquo;</a> <a href="?page=' . ($page - 1) . '" title="Previous page" class="pagination-link">&lsaquo;</a>' : '<span class="disabled">&laquo;</span> <span class="disabled">&lsaquo;</span>';

    // The "forward" link
    //$nextlink = ($page < $pages) ? '<a href="?page=' . ($page + 1) . '" title="Next page">&rsaquo;</a> <a href="?page=' . $pages . '" title="Last page">&raquo;</a>' : '<span class="disabled">&rsaquo;</span> <span class="disabled">&raquo;</span>';
    $nextlink = ($page < $pages) ? '<a href="?page=' . ($page + 1) . '" title="Next page" class="pagination-link">&rsaquo;</a> <a href="?page=' . $pages . '" title="Last page" class="pagination-link">&raquo;</a>' : '<span class="disabled">&rsaquo;</span> <span class="disabled">&raquo;</span>';

    // Prepare the paged query
    $result = $mysqli->prepare("SELECT * FROM data ORDER BY id DESC LIMIT ? OFFSET ?");
    $result->bind_param('ii', $limit, $offset);
    $result->execute();
    if (!$result->execute()) {
        die("Execute failed: (" . $mysqli->errno . ") " . $mysqli->error);
    }

    // Bind the result to variables
    $result->bind_result($id, $timestamp, $temperature, $pressure, $humidity, $rain, $rain_rate, $luminance, $wind_speed, $wind_direction, $day, $week, $month, $year); // Add all columns you need here

    // Display the paging information
    echo '<div id="paging"><p>', $prevlink, ' Page ', $page, ' of ', $pages, ' pages, displaying ', $page * $limit - $limit + 1, '-', min($page * $limit, $total), ' of ', $total, ' results ', $nextlink, ' </p></div>';

    $oddrow = true;

    // Fetch and display the results
    while ($result->fetch()) {
        if ($oddrow) { 
            $css_class=' class="table_cells_odd"'; 
        } else { 
            $css_class=' class="table_cells_even"'; 
        }

        $oddrow = !$oddrow;

        $seconds_in_hour = 3600;
        $rain_rate = $rain_rate * $seconds_in_hour;
        $wind_speed = round($wind_speed * 2.23694, 1);

        $rounded_direction = (int) round($wind_direction);
        switch ($rounded_direction) {
            case 225:
                $wind_direction = "N";
                break;
            case 180:
                $wind_direction = "NW";
                break;
            case 135:
                $wind_direction = "W";
                break;
            case 90:
                $wind_direction = "SW";
                break;
            case 45:
                $wind_direction = "S";
                break;
            case 0:
                $wind_direction = "SE";
                break;
            case 315:
                $wind_direction = "E";
                break;
            case 270:
                $wind_direction = "NE";
                break;
            // add other cases if necessary
            default:
                $wind_direction = "Unknown"; // This will show "Unknown" for any unhandled values
        }

        echo '<tr>';
        echo '   <td'.$css_class.'>'.$id.'</td>';
        echo '   <td'.$css_class.'>'.$timestamp.'</td>';
        echo '   <td'.$css_class.'>'.number_format($temperature,1,'.','').'</td>';
        echo '   <td'.$css_class.'>'.number_format($pressure,1,'.','').'</td>';
        echo '   <td'.$css_class.'>'.number_format($humidity,1,'.','').'</td>';
        echo '   <td'.$css_class.'>'.number_format($rain,1,'.','').'</td>';
        echo '   <td'.$css_class.'>'.number_format($rain_rate,1,'.','').'</td>';
        echo '   <td'.$css_class.'>'.number_format($luminance,1,'.','').'</td>';
        echo '   <td'.$css_class.'>'.number_format($wind_speed,1,'.','').'</td>';
        echo '   <td'.$css_class.'>'.$wind_direction.'</td>';
        echo '   <td'.$css_class.'>'.$day.'</td>';
        echo '   <td'.$css_class.'>'.$week.'</td>';
        echo '   <td'.$css_class.'>'.$month.'</td>';
        echo '   <td'.$css_class.'>'.$year.'</td>';
        echo '</tr>';
    }

    // Close the prepared statement
    $result->close();
    ?>

    </table>
    </body>
</html>
