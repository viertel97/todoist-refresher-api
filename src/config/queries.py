activity_query = """
SELECT
    a.*,
    GROUP_CONCAT(
        CASE
            WHEN c.last_name IS NULL OR c.last_name = '' THEN c.first_name
            ELSE CONCAT(c.first_name, ' ', c.last_name)
        END SEPARATOR '~'
    ) AS people,
    CONCAT(
        DATE_FORMAT(a.happened_at, '%Y-%m-%d'),
        '-',
        a.summary)
    AS filename,
    GROUP_CONCAT(
        DISTINCT e.name SEPARATOR '~'
    ) AS emotions
FROM
    activities AS a
    LEFT JOIN activity_contact AS ac ON a.id = ac.activity_id
    LEFT JOIN contacts AS c ON ac.contact_id = c.id
    LEFT JOIN emotion_activity AS ea ON a.id = ea.activity_id
    LEFT JOIN emotions AS e ON ea.emotion_id = e.id
WHERE
    a.summary != 'TBD' and a.id = {activity_id}
GROUP BY
    a.id
HAVING
    people != 'INBOX'
ORDER BY
    a.happened_at;
                    """
